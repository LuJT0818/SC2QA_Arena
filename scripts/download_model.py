"""并行分块下载 HuggingFace 模型（国内默认走 hf-mirror），只补缺失文件，可重复运行。

为什么不是一个 huggingface-cli download 就完事：
  单连接在国内镜像上大约 3.5MB/s，4GB 要 20 分钟；开 12 个 Range 连接能到 7-8MB/s。
  而且按块写文件，断了重跑只会补没下完的块。

用法：
    python scripts/download_model.py
    python scripts/download_model.py --repo Qwen/Qwen3-1.7B --dest models/Qwen3-1.7B --jobs 12
"""

import argparse
import hashlib
import json
import threading
import time
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CHUNK = 32 * 1024 * 1024          # 每块 32MB
DEFAULT_ENDPOINT = "https://hf-mirror.com"

_lock = threading.Lock()
_done = 0


def list_files(endpoint: str, repo: str) -> list[dict]:
    url = f"{endpoint}/api/models/{repo}/tree/main?recursive=1"
    # 镜像会拦 Python-urllib 的默认 UA，必须伪装成普通客户端
    req = urllib.request.Request(url, headers={"User-Agent": "sc2qa-downloader/1.0"})
    with urllib.request.urlopen(req, timeout=30) as r:
        items = json.load(r)
    return [
        {"path": it["path"], "size": it["size"], "sha256": it.get("lfs", {}).get("oid", "")}
        for it in items
        if it["type"] == "file"
    ]


def fetch_range(url: str, start: int, end: int, retries: int = 6) -> bytes:
    """取 [start, end] 这一段字节，失败重试。"""
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "Range": f"bytes={start}-{end}",
                    "User-Agent": "sc2qa-downloader/1.0",
                    "Accept-Encoding": "identity",
                },
            )
            with urllib.request.urlopen(req, timeout=90) as resp:
                data = resp.read()
            if len(data) == end - start + 1:
                return data
            last = f"期望 {end - start + 1} 字节，实际 {len(data)}"
        except Exception as exc:
            last = f"{type(exc).__name__}: {exc}"
        time.sleep(1.0 * (attempt + 1))
    raise IOError(f"下载 {start}-{end} 失败: {last}")


def download_file(endpoint: str, repo: str, item: dict, dest_dir: Path, jobs: int) -> None:
    global _done
    path = dest_dir / item["path"]
    path.parent.mkdir(parents=True, exist_ok=True)
    size = item["size"]

    if path.exists() and path.stat().st_size == size:
        print(f"[skip] {item['path']} 已完整", flush=True)
        return

    url = f"{endpoint}/{repo}/resolve/main/{item['path']}"
    print(f"[get ] {item['path']}  {size / 1024**3:.2f} GB", flush=True)

    # 先占位成目标大小，避免块写越界
    with open(path, "wb") as f:
        f.truncate(size)

    ranges = [(s, min(s + CHUNK - 1, size - 1)) for s in range(0, size, CHUNK)]
    with ThreadPoolExecutor(max_workers=jobs) as pool:
        futures = {pool.submit(fetch_range, url, s, e): (s, e) for s, e in ranges}
        for fut in as_completed(futures):
            s, e = futures[fut]
            data = fut.result()
            with open(path, "r+b") as f:
                f.seek(s)
                f.write(data)
            with _lock:
                _done += len(data)

    print(f"[ok  ] {item['path']} 下载完成", flush=True)


def verify(path: Path, expect: str) -> bool:
    if not expect:
        return True
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(8 * 1024 * 1024), b""):
            h.update(block)
    ok = h.hexdigest() == expect
    print(f"[{'ok  ' if ok else 'FAIL'}] sha256 {path.name}: {h.hexdigest()[:16]}...", flush=True)
    return ok


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default="Qwen/Qwen3-1.7B")
    ap.add_argument("--dest", default="models/Qwen3-1.7B")
    ap.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    ap.add_argument("--jobs", type=int, default=12, help="并发连接数")
    args = ap.parse_args()

    dest_dir = (ROOT / args.dest).resolve()
    dest_dir.mkdir(parents=True, exist_ok=True)

    files = list_files(args.endpoint, args.repo)
    todo = [f for f in files if not ((dest_dir / f["path"]).exists()
                                     and (dest_dir / f["path"]).stat().st_size == f["size"])]
    total = sum(f["size"] for f in todo)
    print(f"仓库 {args.repo}：{len(files)} 个文件，缺 {len(todo)} 个，共 {total / 1024**3:.2f} GB")
    if not todo:
        print("全部就绪")
        return 0

    stop = threading.Event()

    def reporter():
        last, last_t = 0, time.time()
        while not stop.wait(3):
            with _lock:
                now = _done
            dt = time.time() - last_t
            speed = (now - last) / dt / 1024**2 if dt else 0
            pct = now / total * 100 if total else 0
            print(f"    {pct:5.1f}%  {now / 1024**3:5.2f}/{total / 1024**3:.2f} GB  {speed:5.2f} MB/s", flush=True)
            last, last_t = now, time.time()

    th = threading.Thread(target=reporter, daemon=True)
    th.start()

    start = time.time()
    for item in todo:
        download_file(args.endpoint, args.repo, item, dest_dir, args.jobs)
    stop.set()
    elapsed = time.time() - start

    print(f"\n下载耗时 {elapsed:.0f}s，平均 {total / elapsed / 1024**2:.2f} MB/s")

    bad = [f["path"] for f in files if f["sha256"] and not verify(dest_dir / f["path"], f["sha256"])]
    if bad:
        print("校验失败:", bad)
        return 1
    print("全部文件校验通过")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

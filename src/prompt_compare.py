"""在项目根目录运行：python src/prompt_compare.py"""

import csv
import json
from pathlib import Path

from model_client import ask


ROOT = Path(__file__).resolve().parent.parent
QUESTION_LIMIT = 10  # 改成1，就只比较第一道题。
PREVIEW_ONLY = False  # 改成True，就只保存输入预览。
FIELDS = ["minerals_current", "vespene_current", "workers_active_count"]
NOTES = (
    "N1：minerals_current表示当前矿存量，vespene_current表示当前气存量；"
    "workers_active_count表示活跃工人数，不能直接等同于正在采矿的工人数。"
    "这里只按game_loop编号标识采样点。单个采样点的这些统计不能证明最终胜者。"
)


def build_input(records, case):
    """准备本题数据；T03由程序提供证据，模型不负责查询。"""
    game_loop = case["game_loop"]
    players = {}
    for row in records:
        if row["frame"] == game_loop and row["pid"] in (1, 2):
            players[str(row["pid"])] = {field: row[field] for field in FIELDS}

    # 仅修改本题副本，原始数据文件保持不变。
    if "hide" in case:
        hidden = case["hide"]
        players[str(hidden["pid"])][hidden["field"]] = None

    difference = {}
    for field in FIELDS:
        player1_value = players["1"][field]
        player2_value = players["2"][field]
        if player1_value is None or player2_value is None:
            difference[field] = None
        else:
            difference[field] = player1_value - player2_value

    data = {
        "game_loop": game_loop,
        "players": players,
        "difference_player1_minus_player2": difference,
        "source_id": f"S{game_loop}",
        "source": f"data/processed/organized_records.json，frame={game_loop}，pid=1和2",
        "artificial_missing_test": "hide" in case,
    }
    return (
        f"问题：{case['question']}\n"
        f"本次数据：\n{json.dumps(data, ensure_ascii=False, indent=2)}\n"
        f"字段说明：{NOTES}"
    )


def main():
    # 1. 读取统计数据和问题。
    data_file = ROOT / "data/processed/organized_records.json"
    records = json.loads(data_file.read_text(encoding="utf-8"))
    question_file = ROOT / "eval/dev_A.jsonl"
    cases = []
    for line in question_file.read_text(encoding="utf-8").splitlines():
        if line.strip():
            cases.append(json.loads(line))

    # 2. 准备结果文件，每次运行覆盖同名文件。
    output_dir = ROOT / "results/T03"
    output_dir.mkdir(parents=True, exist_ok=True)
    name = "preview.csv" if PREVIEW_ONLY else "comparison.csv"

    with (output_dir / name).open("w", encoding="utf-8-sig", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(["id", "prompt_version", "input", "reference", "answer"])

        # 3. 每道题分别使用三种提示，调用模型并保存回答。
        for case in cases[:QUESTION_LIMIT]:
            evidence = build_input(records, case)
            for version in ("direct", "rules", "examples"):
                template = (ROOT / f"prompts/{version}.txt").read_text(encoding="utf-8")
                prompt = template + "\n\n" + evidence
                print(f"{case['id']} / {version}", flush=True)
                answer = ""
                if not PREVIEW_ONLY:
                    answer = ask(prompt, max_new_tokens=256)
                    print(answer, flush=True)
                writer.writerow([case["id"], version, prompt, case["reference"], answer])
                file.flush()
    print(f"已保存到：{output_dir / name}")


if __name__ == "__main__":
    main()

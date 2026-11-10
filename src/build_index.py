import json
from pathlib import Path

import numpy as np
from sentence_transformers import SentenceTransformer


ROOT = Path(__file__).resolve().parent.parent
MODEL_NAME = "BAAI/bge-small-zh-v1.5"
NOTES_FILE = ROOT / "knowledge/notes.jsonl"
VECTORS_FILE = ROOT / "knowledge/vectors.npy"


def build_index():
    # 1. 逐行读取资料，按原顺序收集标题和正文。
    texts = []
    with NOTES_FILE.open(encoding="utf-8") as file:
        for line in file:
            if line.strip(): # 检查行是否为空
                note = json.loads(line)
                texts.append(note["title"] + "\n" + note["text"])

    if not texts:
        raise ValueError("资料文件为空，请先填写notes.jsonl。")

    # 2. 加载向量模型。首次运行会下载，文件缓存到项目的models目录。
    model = SentenceTransformer(
        MODEL_NAME,
        cache_folder=str(ROOT / "models"),
        device="cpu",
    )

    # 3. 每条资料转换为一个向量，归一化方便后续比较相似度。
    vectors = model.encode(texts, normalize_embeddings=True, convert_to_numpy=True)

    # 4. 保存数组，第1行向量对应第1条资料，以此类推。
    np.save(VECTORS_FILE, vectors)
    print(f"已转换 {len(texts)} 条资料，向量数组形状为 {vectors.shape}")
    print(f"已保存到 {VECTORS_FILE}")


if __name__ == "__main__":
    build_index()

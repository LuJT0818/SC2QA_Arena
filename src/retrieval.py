import json

import numpy as np
from sentence_transformers import SentenceTransformer

from build_index import MODEL_NAME, NOTES_FILE, ROOT, VECTORS_FILE
from tools import generate_answer


def retrieve(question, top_k=2):
    # 1. 读取资料和向量，向量行号对应资料顺序。
    notes = []
    with NOTES_FILE.open(encoding="utf-8") as file:
        for line in file:
            if line.strip():
                notes.append(json.loads(line))

    vectors = np.load(VECTORS_FILE, allow_pickle=False) 
    if vectors.ndim != 2 or len(vectors) != len(notes) or not notes:
        raise ValueError("资料与向量数量不匹配或资料为空，请重新运行build_index.py。")
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k必须是正整数。")

    # 2. 使用与建索引时相同的模型，将问题转换成向量。
    model = SentenceTransformer(
        MODEL_NAME,
        cache_folder=str(ROOT / "models"),
        device="cpu",
    )
    query_vector = model.encode(
        "为这个句子生成表示以用于检索相关文章：" + question,
        normalize_embeddings=True,
        convert_to_numpy=True,
    )

    # 3. 向量已归一化，点积得到各条资料与问题的余弦相似度。
    scores = vectors @ query_vector
    best_indices = np.argsort(scores)[::-1][:top_k]

    # 4. 按分数从高到低，返回原文、编号、来源和分数。
    results = []
    for index in best_indices:
        result = notes[index].copy()
        result["score"] = float(scores[index])
        results.append(result)
    return results


def answer_with_notes(question):
    # 1. 检索相关说明，先打印出来方便核对。
    results = retrieve(question)
    print("检索到的资料")
    print(json.dumps(results, ensure_ascii=False, indent=2))

    # 2. 整理编号、正文和来源，复用统一的回答入口。
    passages = []
    for note in results:
        passage = {
            "id": note["id"], "title": note["title"],
            "text": note["text"], "source": note["source"],
        }
        passages.append(passage)
    return generate_answer(question, notes=passages)


if __name__ == "__main__":
    question = "双方差值是怎么算的？"
    answer = answer_with_notes(question)
    print("最终回答")
    print(answer)

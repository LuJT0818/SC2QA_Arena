import json
from pathlib import Path

from model_client import ask


PROMPT_FILE = Path(__file__).resolve().parent.parent / "prompts/answer.txt"


def generate_answer(question, stats=None, notes=None):
    # 数值、说明和混合问答共用同一份提示模板。
    rules = PROMPT_FILE.read_text(encoding="utf-8")
    data_text = json.dumps(stats, ensure_ascii=False, indent=2)
    notes_text = json.dumps(notes, ensure_ascii=False, indent=2)
    prompt = (
        f"{rules}\n\n问题：{question}\n"
        f"本次统计数据：\n{data_text}\n\n参考说明：\n{notes_text}"
    )
    return ask(prompt)

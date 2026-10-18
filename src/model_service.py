import json, time
from pathlib import Path
from openai import OpenAI
import os

CONFIG = json.loads(Path("configs/model.json").read_text())

# 从环境变量读取密钥，避免硬编码
api_key = os.getenv(CONFIG["api_key_env"])
api_key = "sk-3b9f5c491c724aedbd688d54e4d485b4"
if not api_key:
    raise RuntimeError(f"环境变量 {CONFIG['api_key_env']} 未设置")

client = OpenAI(
    api_key=api_key,
    base_url=CONFIG["base_url"],
)

def generate(prompt: str, max_tokens: int | None = None, temperature: float | None = None):
    """统一推理入口，替代原 FastAPI 的 /chat 端点"""
    start = time.perf_counter()
    try:
        response = client.chat.completions.create(
            model=CONFIG["model_id"],
            messages=[{"role": "user", "content": prompt}],
            max_tokens=max_tokens or CONFIG["default_max_tokens"],
            temperature=temperature if temperature is not None else CONFIG["default_temperature"],
            timeout=CONFIG["request_timeout_seconds"],
        )
        answer = response.choices[0].message.content
        elapsed = (time.perf_counter() - start) * 1000
        return {
            "answer": answer,
            "elapsed_ms": round(elapsed, 1),
            "model_id": response.model,
        }
    except Exception as e:
        return {
            "error": str(e),
            "status": type(e).__name__,
        }
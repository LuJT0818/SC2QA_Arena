import json
import sys
import os
from pathlib import Path

# 1. 将项目根目录（SC2QA_Arena）加入 sys.path，方便导入和读取 config
root_path = Path(__file__).parent.parent.absolute()
sys.path.append(str(root_path))
os.chdir(root_path) # 切换工作目录到根目录，保证 configs/model.json 能被正确读取

# 2. 直接从同目录下的 model_service 导入
from model_service import generate

CONFIG = json.loads(Path("configs/model.json").read_text())

def ask(prompt, max_tokens=None):
    return generate(prompt, max_tokens=max_tokens)

if __name__ == "__main__":
    print("--- 正常调用 ---")
    print(ask("用一句话介绍星际争霸2。"))

    print("\n--- 长度调整 ---")
    print("短:", ask("简述虫族菌毯的作用。", max_tokens=32))
    print("长:", ask("简述虫族菌毯的作用。", max_tokens=512))

    print("\n--- 错误参数（空 prompt）---")
    print(ask(""))

    print("\n--- 认证失败模拟 ---")
    # 临时用错误密钥初始化客户端后调用
    from openai import OpenAI
    bad_client = OpenAI(api_key="sk-invalid", base_url=CONFIG["base_url"])
    try:
        bad_client.chat.completions.create(
            model=CONFIG["model_id"],
            messages=[{"role": "user", "content": "test"}],
            max_tokens=10,
        )
    except Exception as e:
        print(f"预期认证错误: {type(e).__name__}")
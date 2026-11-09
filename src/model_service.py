from pathlib import Path

import torch
import uvicorn
from fastapi import FastAPI
from pydantic import BaseModel, Field
from transformers import AutoModelForCausalLM, AutoTokenizer


# 1. 启动时加载一次模型，后续请求重复使用。
model_path = Path(__file__).resolve().parent.parent / "models" / "Qwen3-1.7B"
print(f"正在加载模型：{model_path}", flush=True)
tokenizer = AutoTokenizer.from_pretrained(str(model_path))
model = AutoModelForCausalLM.from_pretrained(
    str(model_path),
    torch_dtype="auto",
    device_map="auto",
)
model.eval()
print("模型加载完成", flush=True)

app = FastAPI()


# 2. 约定客户端发来的 JSON 格式。
class ChatRequest(BaseModel):
    prompt: str = Field(min_length=1)
    max_new_tokens: int = Field(default=256, ge=1, le=512)


# 3. 收到 POST /chat 请求后，运行一次模型推理。
@app.post("/chat")
def chat(request: ChatRequest):
    messages = [{"role": "user", "content": request.prompt}]
    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
        enable_thinking=False,
    )
    model_inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.inference_mode():
        generated_ids = model.generate(
            **model_inputs,
            max_new_tokens=request.max_new_tokens,
            do_sample=False,  # T03 比较提示时，固定为非随机生成。
        )

    output_ids = generated_ids[0][len(model_inputs.input_ids[0]):]
    answer = tokenizer.decode(output_ids, skip_special_tokens=True).strip()
    return {"answer": answer}


# 4. 运行这个文件时，启动本机 HTTP 服务。
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8008)

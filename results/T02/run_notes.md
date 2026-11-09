# T02 运行记录

## 模型

- `Qwen/Qwen3-1.7B`，本地 `models/Qwen3-1.7B/`，3.80 GB，BF16
- 下载：`python scripts/download_model.py`（12 连接分块并行，591 s，平均 6.56 MB/s，逐文件 sha256 通过）

## 环境

- Windows / Python 3.11.17（conda `sc2qa`）
- torch 2.14.1+cu126 / transformers 5.20.2 / fastapi 0.156.4 / uvicorn 0.54.0
- GPU：RTX 3060 Laptop 6 GB

## 代码

| 文件 | 行数 | 作用 |
|---|---|---|
| `src/model_core.py` | 55 | 加载 + `generate()` |
| `src/model_service.py` | 37 | HTTP `/health`、`/chat` |
| `src/model_client.py` | 40 | `ask()` 调用 |
| `configs/model.json` | 7 | 配置 |

## 实测

| 场景 | 结果 |
|---|---|
| 模型加载 | 约 7 s |
| 直接生成（`model_core.py`） | 正常出答案 |
| 短回答 14 token | 892.9 ms 服务端 / 925 ms 客户端 |
| 限 32 token | 1.1 - 2.3 s |
| 稳态 | 约 20 tok/s |

## 一次排错记录

- **现象**：`python src/model_service.py` 1 秒内退出、日志为空，`curl /health` 连接被拒。
- **定位**：`python -c "import src.model_service"` 能导入但 `vars(module)` 为空 → 模块体没执行；
  `ls -la src/*.py` 发现 `model_service.py` 和 `model_client.py` 都是 0 字节（15:30 被清空过）。
- **原因**：空文件被执行，所以"成功退出且无输出"。
- **处理**：恢复文件后正常。教训：进程秒退且无输出，先查文件大小。

- **现象**：通过服务调用 32 token 要 5.1 s，而直接调用只要 1.25 s。
- **原因**：测试时另一个进程也加载了模型，两份权重共 7.6 GB 超出 6 GB 显存，溢出到系统内存。
- **处理**：确保同一时间只有一个进程加载模型后，重新测得 1.1 - 2.3 s。

## 已知限制

- 6 GB 显存只能同时跑一份模型；`max_new_tokens` 超过 512 时要留意显存。
- 单进程串行推理，两个请求同时来会排队。
- 接口只有 `prompt` 和 `max_new_tokens`，不是 OpenAI 兼容协议。

## 本目录

| 文件 | 内容 |
|---|---|
| `direct_generate.log` | 不启服务，直接生成的输出 |
| `service.log` | 服务启动与请求日志 |
| `client.log` | 客户端三次调用的输出与耗时 |
| `run_notes.md` | 本文件 |

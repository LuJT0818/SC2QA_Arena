# 项目环境配置说明

> 记录时间：2026-10-22（T02 完成时）。所有数值为本机实测，不是估计值。
> 换机器或重装环境时，照第九节复现。

## 一、机器与系统

| 项目 | 值 |
|---|---|
| 主机名 | Yoimiya |
| 操作系统 | Windows，内核 10.0.26200（64 位） |
| CPU | AMD Ryzen 7 6800H with Radeon Graphics |
| 内存 | 15.2 GB |
| 项目所在盘 | E:，可用约 1.37 TB |

## 二、GPU 与 CUDA

| 项目 | 值 |
|---|---|
| GPU | NVIDIA GeForce RTX 3060 Laptop GPU |
| 显存 | 6144 MiB（约 6 GB），空闲时约 5.0 GB 可用 |
| 显卡驱动 | 616.92 |
| CUDA（torch 内置运行时） | 12.6 |
| cuDNN | 9.10.2（91002） |
| `torch.cuda.is_available()` | True |

显存约束：Qwen3-1.7B 的 BF16 权重占 3.8 GB，**同一时间只能有一个进程加载模型**。
两个进程同时加载会溢出到系统内存，速度掉到约三分之一。

## 三、Python 环境

| 项目 | 值 |
|---|---|
| 管理方式 | conda |
| 环境名 | `sc2qa` |
| 解释器路径 | `C:\Users\26339\miniconda3\envs\sc2qa\python.exe` |
| 版本 | CPython 3.11.17，64 位 |

```bash
conda activate sc2qa
python -c "import torch; print(torch.__version__, torch.cuda.is_available())"
# 期望：2.14.1+cu126 True
```

VS Code：`Ctrl+Shift+P` → `Python: Select Interpreter` → 选上面那个路径。
项目里 `.vscode/settings.json` 已把 conda 设为默认环境管理器。

注意：机器上另有一个 Python 3.13（`C:\Users\26339\.workbuddy\binaries\python\versions\3.13.12`），
它是工具链自带的，**没有装本项目依赖**。跑项目一律用 `sc2qa`。

## 四、依赖版本

| 包 | 版本 | 用途 |
|---|---|---|
| torch | 2.14.1+cu126 | 张量计算、GPU |
| transformers | 5.20.2 | 加载模型、对话模板 |
| tokenizers | 0.23.3 | 分词 |
| safetensors | 0.8.0 | 权重文件格式 |
| accelerate | 1.15.0 | 设备放置 |
| fastapi | 0.156.4 | HTTP 服务 |
| uvicorn | 0.54.0 | ASGI 服务器 |
| pydantic | 2.14.1 | 请求参数校验 |
| requests | 2.34.2 | 客户端调用 |
| numpy | 2.4.6 | 数值处理 |
| sc2reader | 1.9.0 | 解析 .SC2Replay |

两个依赖文件的分工：

- `requirements.txt`：本环境全量锁定，142 项，UTF-8。用于完整复现。
- `requirements-model.txt`：T02 需要的最小集合，带安装说明。日常重装环境用它。

**torch 必须从 CUDA 专用索引安装**，否则会装成 CPU 版（`cuda.is_available()` 为 False）：

```bash
pip install torch --index-url https://download.pytorch.org/whl/cu126
pip install -r requirements-model.txt
```

## 五、模型

| 项目 | 值 |
|---|---|
| 模型 | `Qwen/Qwen3-1.7B` |
| 本地目录 | `models/Qwen3-1.7B/`（已被 `.gitignore` 排除，不进版本库） |
| 体积 | 3.80 GB，311 个张量，数据类型 BF16 |
| 分片 1 | `model-00001-of-00002.safetensors` 3.20 GB，sha256 `169ad53ec313c3a3…` |
| 分片 2 | `model-00002-of-00002.safetensors` 0.58 GB，sha256 `912becff8d60672a…` |
| 加载精度 | CUDA 上 `bfloat16`，CPU 上 `float32`（由 `model_core.py` 自动选） |
| 对话模板 | Qwen3 模板，`enable_thinking=False`（关闭思考过程，只要短答案） |
| 获取方式 | `python scripts/download_model.py`，12 连接分块并行，591 s，平均 6.56 MB/s，逐文件校验 sha256 |

## 六、回放数据

| 项目 | 值 |
|---|---|
| 文件 | `data/raw/SvS_G2.SC2Replay` |
| 大小 | 320,571 字节 |
| sha256 | `b1b573b63a0fabde67391496eafdc7bec93279e1f683ad5593ef45a10f24b586` |
| 解析器 | sc2reader 1.9.0 |
| 已导出 | `organized_records.json`（2 玩家 × 3 个共同采样点 = 6 条）、`raw_stats_events.json` |
| 采样时刻 | `second` = 120 / 300 / 480，对应 `frame` = 1920 / 4800 / 7680 |

## 七、与环境相关的文件

| 路径 | 作用 |
|---|---|
| `configs/model.json` | 模型路径、端口、生成长度、温度（5 个键，扁平） |
| `src/model_core.py` | 加载模型 + `generate()` |
| `src/model_service.py` | HTTP 服务，`/health` 与 `/chat` |
| `src/model_client.py` | 调用方 |
| `src/check_env.py` | 环境自检：torch / CUDA / 显存 / 模型文件 / 磁盘 |
| `scripts/download_model.py` | 模型下载（并行分块 + sha256 校验） |
| `results/T02/` | 本卡的运行日志与 `run_notes.md` |

## 八、启动与验证

```bash
conda activate sc2qa
cd E:/AFile/SC2QA_Arena

python src/check_env.py      # 环境自检，最后一行应为"自检通过"
python src/model_core.py     # 不启服务，直接生成一句
python src/model_service.py  # 终端 1：监听 127.0.0.1:8008
python src/model_client.py   # 终端 2：调用
```

服务起来后可以手测：

```bash
curl http://127.0.0.1:8008/health
curl -X POST http://127.0.0.1:8008/chat -H "Content-Type: application/json" -d "{\"prompt\":\"你好\"}"
```

## 九、性能基线（BF16 / CUDA）

| 场景 | 耗时 |
|---|---|
| 模型加载（从磁盘到显存） | 约 7 s，每次启动一次 |
| 短回答 14 token | 893 ms |
| 限 32 token | 1.1 – 2.3 s |
| 稳态生成速度 | 约 20 tok/s |

同机不同时刻会有波动（笔记本功耗、后台占用）。**测速前先确认没有别的进程加载着模型**，
否则两份权重 7.6 GB 超过 6 GB 显存，数字会变成三倍慢。

## 十、已知限制与失败处理

| 现象 | 原因 | 处理 |
|---|---|---|
| `cuda.is_available()` 为 False | 装成了 CPU 版 torch | `pip uninstall torch -y` 后从 cu126 索引重装 |
| `CUDA out of memory` | 另一个进程也加载了模型 | 关掉多余终端；或降 `max_new_tokens` |
| 答案是空的 | 思考模式没关，或 `max_new_tokens` 太小 | 确认 `enable_thinking=False`，先用 256 |
| 客户端报 ConnectionError | 服务没启动 | 先 `python src/model_service.py` |
| `Address already in use` | 8008 端口被占 | 改 `configs/model.json` 的 `port` |
| 服务秒退且无任何输出 | 源文件是空的（0 字节） | `ls -la src/*.py` 查文件大小 |
| `dtype` 报未知关键字 | transformers 是 4.x | 把 `dtype=` 改成 `torch_dtype=` |
| 显存 6 GB 装不下更大模型 | 硬件限制 | 换 3B 以下模型，或改 8bit/4bit 量化 |

其它限制：

- 单进程串行推理，两个请求同时到会排队，第二个耗时翻倍。
- 接口只有 `prompt` 和 `max_new_tokens`，不是 OpenAI 兼容协议。
- 只在本机 `127.0.0.1` 上监听，供本机程序调用；不对外网开放。

## 十一、换机器复现步骤

1. 装 Miniconda，创建环境：`conda create -n sc2qa python=3.11 -y`，激活。
2. 装 GPU 版 torch：`pip install torch --index-url https://download.pytorch.org/whl/cu126`
   （CUDA 版本按新机器驱动选）。
3. 装其余依赖：`pip install -r requirements-model.txt`
4. 验证显卡：`python -c "import torch;print(torch.cuda.is_available())"` 必须为 True。
5. 下模型：`python scripts/download_model.py`（约 4 GB，可用 `--jobs` 调并发）。
6. 自检：`python src/check_env.py`，应输出"自检通过"。
7. 直接生成：`python src/model_core.py`。
8. 起服务 + 调用：`python src/model_service.py` 与 `python src/model_client.py`。
9. 把新机器的设备信息补进本文档第一、二节。

## 十二、待处理

- **旧密钥**：`configs/model.json` 与旧版 `src/model_service.py` 曾硬编码 DeepSeek API key，
  并已进入 git 历史（提交 `d42a1c5`）。该 key 应作废重发。
- **`requirements.txt` 编码**：原文件是 UTF-16，`pip install -r` 会解码失败。
  已重新生成为 UTF-8 全量锁定（`git diff requirements.txt` 可看差异，旧版仍在 git 历史里）。
- **`docs/fields.md` 为空**：T01 要求记录字段来源，需要补。
- **`src/prase_replay.py` 文件名拼写**：`prase` 应为 `parse`，改名时注意同步引用。

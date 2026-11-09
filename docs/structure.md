# 项目目录结构

> 生成时间 2026-10-22，基于实际文件系统，括号内为真实体积。

## 一、目录树

```
SC2QA_Arena/
├── configs/                        配置
│   └── model.json                  模型路径 / 端口 / max_new_tokens / temperature
├── data/                           原始数据（只读，不改）
│   └── raw/
│       └── SvS_G2.SC2Replay        回放 A，313 KB
├── docs/                           文档
│   ├── environment.md              环境配置说明：机器 / GPU / 依赖 / 模型 / 启动 / 排错
│   ├── T02.md                      T02 实现说明：三个文件做什么、怎么跑
│   └── fields.md                   字段说明（目前 0 字节，T01 待补）
├── models/                         模型权重（gitignore，不进版本库）
│   └── Qwen3-1.7B/                 Qwen3-1.7B，3.8 GB，29 个文件
│       ├── config.json
│       ├── model-00001-of-00002.safetensors   3.20 GB
│       ├── model-00002-of-00002.safetensors   0.58 GB
│       ├── model.safetensors.index.json
│       ├── tokenizer.json / tokenizer_config.json
│       └── vocab.json / merges.txt / LICENSE 等其余文件
├── results/                        每张卡的运行记录
│   └── T02/
│       ├── direct_generate.log     不启服务直接生成的输出
│       ├── service.log             服务启动与请求日志
│       ├── client.log              客户端三次调用与耗时
│       └── run_notes.md            模型版本 / 环境 / 实测数字 / 排错记录
├── scripts/                        一次性工具脚本
│   └── download_model.py           并行分块下载模型 + sha256 校验
├── src/                            源码
│   ├── model_core.py               加载模型 + generate()
│   ├── model_service.py            HTTP 服务：/health、/chat
│   ├── model_client.py             调用方（requests）
│   ├── check_env.py                环境自检：torch / CUDA / 显存 / 模型文件 / 磁盘
│   └── prase_replay.py             解析回放，导出统计记录
├── .gitignore                      排除 models/、__pycache__、密钥、Office 临时文件
├── README.md                       sc2reader 学习笔记（不是运行说明）
├── requirements.txt                全量依赖锁定，142 项，UTF-8
├── requirements-model.txt          T02 最小依赖 + torch 的 CUDA 安装命令
├── organized_records.json          整理后的 6 条统计记录（2 玩家 × 3 个采样点）
├── raw_stats_events.json           回放中全部 PlayerStatsEvent 原始值
├── sc2reader_test.py               试探 sc2reader 字段的临时脚本
├── SC2回放问答与模型对比系统_任务书.docx   任务书
└── 789853.jpg                      702 KB 图片，用途未标注
```

`.git/`、`__pycache__/`、`.vscode/`、`.workbuddy/` 属于工具目录，不在上图中。

## 二、每个目录管什么

| 目录 | 职责 | 什么时候往里加东西 |
|---|---|---|
| `configs/` | 参数，代码里不写死 | 加新配置项、加教师模型配置（T10） |
| `data/raw/` | 原始回放，只读 | 下载回放 B、C（T04） |
| `data/processed/` | 解析出的统计表 | **目前还没有**，T01 要求建 |
| `docs/` | 说明与字段依据 | 每张卡写一份 |
| `models/` | 本地权重 | 换模型时 |
| `results/Txx/` | 每张卡的运行记录 | 每完成一张卡建一个 |
| `scripts/` | 一次性工具 | 下载、批量转换这类 |
| `src/` | 会被 import 的代码 | 主程序都放这里 |

约定：**跑一次就完的工具进 `scripts/`，会被别的代码 import 的进 `src/`。**

## 三、当前数据流

```
data/raw/*.SC2Replay
        │  src/prase_replay.py
        ▼
organized_records.json（6 条核对过的记录）
        │  src/model_client.py 组装成提示词
        ▼
HTTP POST /chat  →  src/model_service.py  →  model_core.generate()  →  模型（显存）
        ▼
答案 + 耗时（results/T02/client.log）
```

## 四、和目录有关的三件事

1. **`data/processed/` 还不存在**。T01 要求把统计表放这里，和 `data/raw/` 分开，现在只有 raw。
2. **`README.md` 目前是 sc2reader 学习笔记**，不是项目说明。T00 要求 README 里有"环境与运行步骤"，
   这块内容现在在 `docs/environment.md` 里，README 里没有入口。
3. **根目录有两处杂物**：`789853.jpg`（702 KB，未标注用途）、`sc2reader_test.py`（临时试探脚本，
   按约定应移入 `scripts/` 或删掉）。

另外 `src/prase_replay.py` 的文件名把 `parse` 拼成了 `prase`，改名时记得同步改引用。

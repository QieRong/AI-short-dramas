# AI Short Dramas · AI 短剧流水线

> 用 **0 元预算**产出 **50 集 AI 短剧**（剧本 + 成片）的开源流水线项目。
> 首个里程碑是跑通 1 集端到端流程，验证可行性与零成本前提后，再放量到 50 集。

[![Repo](https://img.shields.io/badge/repo-AI--short--dramas-blue)](https://github.com/QieRong/AI-short-dramas)
[![License](https://img.shields.io/badge/license-CC%20BY--NC%204.0-lightgrey)](#许可声明)

---

## 这是什么

一个把"写剧本 → 出分镜 → 生成角色图 → 生成视频 → 配音 → 合成"全流程脚本化、可复现的短剧生产工具链。
全部环节使用**免费额度或本地免费工具**，不接入任何需要绑卡 / 充值 / 订阅的服务。

**核心约束（本项目成立的前提）**

| 约束 | 说明 |
| --- | --- |
| 预算 0 元 | 禁用一切付费调用；发现收费立即停止 |
| 本机无 AI 算力 | i5-6200U + 920MX（约 2GB 显存），**不做本地视频生成**，算力全部走云端 |
| 本机定位 | 文本调度 + 素材组装 + FFmpeg 合成，不是渲染节点 |

---

## 技术栈

| 环节 | 工具 / 模型 | 成本 |
| --- | --- | --- |
| ① 剧本 | Agnes `agnes-3.0-flash` | 免费 |
| ② 分镜 | Agnes `agnes-3.0-flash` | 免费 |
| ③ 角色图 | Agnes `agnes-image-2.5-flash` | 免费 |
| ④ 分镜图 | Agnes `agnes-image-2.5-flash` | 免费 |
| ⑤ 视频片段 | Agnes `agnes-video-2.5-flash` | 免费（限时） |
| ⑥ 配音 | [Edge-TTS](https://github.com/rany2/edge-tts) | 免费 |
| ⑦ 合成 | 本机 FFmpeg | 免费 |

- **Agnes API**：OpenAI 风格接口，认证走 `Authorization: Bearer <KEY>`
  - 中国站 `https://api.agnes-ai.cn/v1` ｜ 国际站 `https://apihub.agnes-ai.com/v1`
  - 官方文档：https://wiki.agnes-ai.com
  - ⚠️ 密钥与站点绑定，两站不互通
- **Edge-TTS**：唯一外部 Python 依赖，无需 API Key
- **FFmpeg**：负责运镜（Ken Burns）、抽帧、拼接、混音、烧字幕

---

## 目录结构

```
AI-short-dramas/
├── 00_bible/        世界观、人物小传、剧集圣经
├── 01_outline/      50 集分集大纲
├── 02_scripts/      剧本正文（EP01.md ... EP50.md）
├── 03_storyboard/   分镜脚本（EP01_storyboard.md ...）
├── 04_assets/
│   ├── characters/  角色图（含生成清单 _manifest*.json）
│   ├── scenes/      场景图
│   ├── video/       视频片段 + 抽帧衍生品（不入库）
│   └── audio/       配音（不入库）
├── 05_final/        成片输出（不入库）
├── scripts/         工具脚本（Python）
└── docs/            项目文档（AGENTS.md 规范、PROGRESS.md 进度、分镜规范）
```

---

## 快速开始

### 1. 环境准备

```bash
# 配置密钥（任选其一）
#   方式 A：复制模板为 .env 并填入真实密钥（.env 已被忽略，不会提交）
cp scripts/.env.example scripts/.env

#   方式 B：设置系统环境变量（推荐）
#   PowerShell:  setx AGNES_API_KEY "你的密钥"    # 设置后需重启会话
```

### 2. 环境自检

```bash
cd scripts
python check_env.py
```

检查项：密钥是否就绪、FFmpeg 是否可用、依赖是否齐全、磁盘空间是否充足。

### 3. 脚本用途

| 脚本 | 用途 |
| --- | --- |
| `check_env.py` | 环境自检（密钥 / FFmpeg / 依赖 / 磁盘） |
| `agnes_client.py` | 统一调用封装（配置、密钥读取、错误类型） |
| `agnes_text.py` | 文本调用（剧本 + 分镜共用） |
| `agnes_image.py` | 图像调用（角色图 + 分镜图共用） |
| `agnes_video.py` | 视频任务提交 + 轮询 + 下载 |
| `kenburns.py` | 准视频生成（静态图 + FFmpeg 运镜） |
| `extract_frames.py` | 视频抽帧（散图 + 长图 / 平移对比图） |
| `tts_narrate.py` | Edge-TTS 批量配音 |
| `compose_video.py` | FFmpeg 拼接、混音、烧字幕 |
| `gen_characters.py` | 角色图批量生成 |
| `gen_linqian_scar*.py` | 角色图局部修改（图生图补疤痕） |
| `test_*.py` | 额度 / 限流探测脚本 |

> **注**：单集编排器 `run_episode.py` 尚在规划中，当前各环节脚本可独立调用。

### 4. 运行

```bash
cd scripts

# 环境自检
python check_env.py

# 生成角色图
python gen_characters.py

# 生成视频片段（详见脚本内 docstring 参数说明）
python agnes_video.py --help
```

> 单集编排器 `run_episode.py` 尚在规划中，当前按环节逐个调用脚本。

---

## 仓库公开策略

本项目采用 **"除密钥外全部公开"** 策略（2026-10-10 决策）：

| 类别 | 处置 |
| --- | --- |
| 密钥（`.env`） | ❌ 唯一排除 |
| 剧本、分镜、剧集圣经 | ✅ 公开 |
| 角色设定、角色图 | ✅ 公开 |
| 记忆文件 | ✅ 公开 |
| 生成脚本 | ✅ 公开 |
| 视频、音频 | ❌ 体积大，不入库 |
| 抽帧衍生品 | ❌ 可重新生成，不入库 |

> 判断准则只有一条：**"它含密钥吗？"** 含则排除，不含则公开。

---

## 许可声明

**本项目采用 [CC BY-NC 4.0](https://creativecommons.org/licenses/by-nc/4.0/deed.zh) 许可。**

简言之：

| 允许 | 要求 | 禁止 |
| --- | --- | --- |
| ✅ 学习、研究、二次创作 | 📌 署名原作者并注明来源 | ❌ 商业用途 |
| ✅ 复制、分发 | 📌 相同方式共享 | ❌ 去除署名 |

- **剧本、角色设定、剧集圣经等原创内容**：任何人可访问、学习、非商业性二次创作，**需署名**。
- **代码与脚本**：同样适用上述许可。
- **如需商业使用，请先联系作者获取授权。**

---

## 相关文档

| 文档 | 内容 |
| --- | --- |
| [`AGENTS.md`](AGENTS.md) | 项目级 Agent 行为契约（规范、约束、纪律） |
| [`docs/PROGRESS.md`](docs/PROGRESS.md) | 当前进度、待办、实测数据 |
| [`docs/分镜规范.md`](docs/分镜规范.md) | 分镜编写与交付自检标准 |
| [`.workbuddy/memory/MEMORY.md`](.workbuddy/memory/MEMORY.md) | 长期决策与实测事实 |

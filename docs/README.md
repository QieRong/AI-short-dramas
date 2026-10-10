# AI 短剧项目 · 零成本制作流水线

## 项目定位

50 集 AI 短剧（剧本 + AI 成片），**预算 0 元**，全部使用免费额度完成。

## 核心架构决策

| 环节 | 方案 | 成本 |
|---|---|---|
| 剧本/分镜（文本） | Agnes 文本模型 `agnes-3.0-flash` | 免费 |
| 角色图/分镜图 | Agnes 图像模型 `agnes-image-2.5-flash` | 免费 |
| 视频片段 | Agnes 视频模型 `agnes-video-2.5-flash` | 免费（限时） |
| 配音 | Edge-TTS | 免费 |
| 合成 | 本机 FFmpeg | 免费 |

**本机硬件约束**（决定性）：i5-6200U + NVIDIA 920MX（约 2GB 显存），**无法本地跑视频生成**，全部依赖 Agnes 云端 API。

## 目录结构

```
AI-short-dramas/
├── 00_bible/        世界观、人物小传、总纲
├── 01_outline/      50 集分集大纲
├── 02_scripts/      剧本正文
├── 03_storyboard/   分镜脚本
├── 04_assets/       素材
│   ├── characters/  角色图
│   ├── scenes/      场景图
│   ├── video/       视频片段
│   └── audio/       配音
├── 05_final/        成片
├── scripts/         工具脚本
└── docs/            文档
```

## Agnes API 接入

- 中国站 Base URL：`https://api.agnes-ai.cn/v1`
- 国际站 Base URL：`https://apihub.agnes-ai.com/v1`
- 认证：`Authorization: Bearer <AGNES_API_KEY>`
- 密钥来源：**环境变量 `AGNES_API_KEY`**，绝不写入文件

### 脚本清单

| 脚本 | 职责 |
|---|---|
| `agnes_client.py` | 核心：配置加载、密钥读取、HTTP 请求（含重试） |
| `agnes_text.py` | 文本生成 |
| `agnes_image.py` | 图像生成 |
| `agnes_video.py` | 视频生成（创建任务 + 轮询 + 下载） |
| `tts_narrate.py` | Edge-TTS 配音 |
| `compose_video.py` | FFmpeg 合成 |
| `check_env.py` | 环境自检 |

## 使用步骤

### 1. 配置密钥（必须手动执行）

```powershell
setx AGNES_API_KEY "你的密钥"
```
执行后**需重启 WorkBuddy 会话**使变量生效。

### 2. 环境自检

```bash
cd scripts
python check_env.py
```

### 3. 生成剧本

```bash
python agnes_text.py --prompt "写一集30秒短剧剧本..." --out ../02_scripts/EP01.md
```

### 4. 生成角色图 / 分镜图

```bash
python agnes_image.py --prompt "角色设定图：..." --out ../04_assets/characters/hero.png
```

### 5. 生成视频片段

```bash
python agnes_video.py --prompt "镜头描述..." --out ../04_assets/video/ep01_shot1.mp4
```

### 6. 配音

```bash
python tts_narrate.py --text "台词" --out ../04_assets/audio/line01.mp3
```

### 7. 合成成片

```bash
python compose_video.py --clips ../04_assets/video/*.mp4 --audio ../04_assets/audio/line01.mp3 --out ../05_final/EP01.mp4
```

## 待办

- [ ] 用户写入 `AGNES_API_KEY` 环境变量
- [ ] 验证 Agnes 三类模型端点实际可用性
- [ ] 跑通 1 集完整流程
- [ ] 核对实际计费是否为零
- [ ] 决定是否放量到 50 集

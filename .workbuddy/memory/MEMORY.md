# AI-short-dramas 项目长期记忆

## 项目目标
制作 50 集 AI 短剧（剧本 + AI 成片），先用 WorkBuddy 免费 DeepSeek 额度完成文本创作，成片阶段走外部工具。

## 硬件约束（决定性）
- 本机为 2015 年轻薄本：i5-6200U（2核）+ Intel HD 520 核显 + NVIDIA 920MX（~2GB 显存）
- **本地 AI 视频生成本机不可行**：所有开源方案最低需 8GB 显存
- 定位：本机只做文本、分镜、脚本编排、ffmpeg 合成；重算力走云端

## 已确认的环境
- Python 3.13.14（托管）、Node 22.22.2（托管）、Git 2.55.0 均已就绪
- ffmpeg：未入 PATH；已有便携版在 `C:\Program Files\File Converter\ffmpeg.exe`
- WorkBuddy 积分：约 2,600（平台内任务额度，不可导出为 API Key）

## 技术路线决策
- 文本与分镜：WorkBuddy 对话式生成（额度内）+ 可选 DeepSeek 官方 API 脚本批量
- 视频生成：云端 API（即梦/Vidu/可灵/通义万相）为唯一可行路径，成本大头
- 合成：本地 ffmpeg
- 参考开源框架：shuohao-skills（零依赖、可移植到 WorkBuddy skills）、LocalMiniDrama

## 仓库与安全约定（长期）
- GitHub 仓库：https://github.com/QieRong/AI-short-dramas（公开）
- **策略：全量上传作品内容（剧本/分镜/文档/脚本），唯一排除项 = API 密钥与一切 `.env`**
- 用户用途：用 DeepSeek 对照仓库内容审查与续写剧本
- `.gitignore` 已覆盖：`.env`（全层级）、所有图片/视频/音频、临时日志
- **每次推送前必做**：`git check-ignore -v scripts/.env` + 全历史 `sk-` 密钥扫描
- 密钥配置：`scripts/.env`（本地，已忽略）或系统环境变量 `AGNES_API_KEY`

## Agnes API 关键事实（已实测核实）
- 站点：国际站 `https://apihub.agnes-ai.com/v1`（当前密钥为国际站签发）
- 模型：文本 `agnes-3.0-flash` / 图像 `agnes-image-2.5-flash` / 视频 `agnes-video-2.5-flash`
- **视频 schema（官方）**：`mode` = "text"/"keyframe"/"reference"；`seconds` 字符串 "4"-"12"；
  `size` = "720P"；画幅用 `aspect_ratio`（竖屏 "9:16"→720x1280）；查询 `GET /agnesapi?video_id=&model_name=`
- **图像支持图生图**：`extra_body.image = ["data:image/png;base64,..."]`，size 用 "1K"/"2K"+`ratio`
- **视频免费层限流严重**：实测连续调用即 429，5 分钟未恢复（待 24h 后复测确认是否日配额）
- 图像与文本：免费可用，无问题

## 角色护照（已选定）
- 林浅：`林浅_护照_补疤img2img_1_半身露腕.png`（基于候选#3 图生图补左腕旧疤）
- 顾承泽：`顾承泽_护照.png`（候选#3 定版）
- 说明文件：`04_assets/characters/角色形象说明.md`

## 创作规范（长期）
- **一个 5 秒片段 = 一个主体动作**（不加长，只拆分）
- 每稿定稿前必附"交付前自检清单"（见 EP01/EP02.md 末尾）
- 分镜规范：`docs/分镜规范.md`（v1.0）
- 台词单句 ≤15 字；每集伏笔 ≤1 个；结尾定格未完成动作

## 待确认事项
- 成片预算上限（L3 资金决策）
- 是否已有 DeepSeek 官方 API Key（用户需要用于对照审查剧本）

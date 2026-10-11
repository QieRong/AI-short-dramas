# AI-short-dramas 项目长期记忆

## 项目目标
制作 50 集 AI 短剧（剧本 + AI 成片），先用 WorkBuddy 免费 DeepSeek 额度完成文本创作，成片阶段走外部工具。

## 硬件约束（决定性）
- 本机为 2015 年轻薄本：i5-6200U（2核）+ Intel HD 520 核显 + NVIDIA 920MX（~2GB 显存）
- **本地 AI 视频生成本机不可行**：所有开源方案最低需 8GB 显存
- 定位：本机只做文本、分镜、脚本编排、ffmpeg 合成；重算力走云端

## 已确认的环境
- Python 3.13.14（托管）、Node 22.22.2（托管）、Git 2.55.0 均已就绪
- ffmpeg：便携版 `C:\Program Files\File Converter\ffmpeg.exe`（7.1，实测可用）；
  WinGet 另装了 9.0.2 full build（`...\WinGet\Packages\Gyan.FFmpeg*\ffmpeg-*\bin\`），
  但 `...\WinGet\Links\` 下的别名桩是 **0 字节、不可执行**——定位外部可执行文件必须**实测运行**，勿只看存在性
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
  （`2K`+`9:16` = **1472×2624**）；脚本 `agnes_image.py` 已支持 `--ref`（可多张，本地图自动转 Data URI）/`--ratio`/`--size 2K`
- ⚠️ **图像脚本的经验**：传入护照作参考图时，模型会**偏向保留人物面部**，弱化提示词要求的"极端特写"裁切 → 需特写时应在提示词中显式声明"画面中不出现面部"
- **视频免费层限流严重**：实测连续调用即 429，5 分钟未恢复
- **视频计费（官方文档 2026-10-11 核实）**：`agnes-video-2.5-flash` 原价 $0.025/秒、**现价 $0（限时免费）**；
  非 Flash 版 `agnes-video-2.5` 才按秒计费（第三方所说 ¥0.15/秒 指后者，与本项目选型无关）
- 图像与文本：免费可用，无问题
- ✅ **2026-10-11 密钥已恢复**：用户重签 Key 后单次调用即成功（intl 端点 200）。
  先前 401 系**旧 Key 失效/被停用**，与站点错配无关；站点配置 `site: intl` 本就正确
- **若再遇 401**：官方成因 = Key 不正确 / 已过期 / 格式错误 / Bearer 后缺空格 / Key 属于其他账户（站点不匹配）
- **站点切换（2026-07-29 公告）**：国际站 Key ↔ `apihub.agnes-ai.com/v1`；国内站 Key ↔ `apihub.agnes-ai.cn/v1`（仅改 `agnes_config.yaml` 的 `site` 字段）
- 免费层文本 RPM = 10（2026-09 调整）；官方明确保留**滥用防范**作为调整维度

## 角色护照（已选定）
- 林浅：`林浅_护照.png`（目视含左腕可辨旧疤，护照已定版；`补疤` 中间产物不在磁盘，**勿再引用旧文件名**）
- 顾承泽：`顾承泽_护照.png`（候选#3 定版）
- 说明文件：`04_assets/characters/角色形象说明.md`

## 分镜图提示词（第④步）关键事实
- 文档：`03_storyboard/EP{nn}_分镜图提示词.md`（EP01 已完成，2026-10-11）
- 参数固化：`agnes-image-2.5-flash` + `size:"2K"` + `ratio:"9:16"`（1472×2624）；
  `response_format` **必须**置于 `extra_body` 内；图生图**不要**传 `tags:["img2img"]`
- 每镜三段式：**画面描述 + 图像提示词 + 参考资产（护照）**；提示词须写入选定角色关键特征
- 场景锚点：EP01 为单一场景「地下室档案室（昏暗 + 应急灯冷光）」；
  B. 宴会厅走廊（奢华）/ C. 地下车库（雨夜）为 EP02+ 预留
- 与 `EP{nn}_视频提示词.md`（第⑤步）**一一对应**：分镜图即视频 i2v 的首帧参考
- ⚠️ 待裁定：剧集圣经标注顾承泽「金丝眼镜（战斗时摘除）」，当前分镜表按用户指令**保留眼镜**

## 合成链路（第⑦步）关键事实
- `compose_video.find_ffmpeg()/find_ffprobe()` 已改为「实测可运行」才采纳（`_runs()`），并枚举 WinGet 真实安装目录
- `kenburns.py` / `extract_frames.py` 仍**硬编码** File Converter 路径（技术债，未统一）
- **ffmpeg concat 清单必须写绝对路径**：相对路径以「清单所在目录」为基准，会二次拼接致找不到
- 合成临时目录 `scripts/.tmp_compose/`（已加入 .gitignore）
- 2026-10-11 首次端到端合成通过：4 段准视频 → 720x1280 / 30fps / 20s

## 配音（第⑥步）关键事实
- Edge-TTS 完全免费、**无需任何 API Key**（与 Agnes 密钥无关，密钥失效期间仍可用）
- 音色：林浅 = `zh-CN-XiaoxiaoNeural`；顾承泽 = `zh-CN-YunxiNeural`（语速 −5% ~ −8%）
- ⚠️ **`--rate` 必须单 token 传 `--rate=-8%`**：edge_tts 用 argparse，拆成
  `["--rate","-8%"]` 会把 `-8%` 当选项 → 负语速无法表达（已修复 `tts_narrate.py`）
- 命名：逐句 `AUD_EP{nn}_S{nn}.mp3`；整集音轨 `AUD_EP{nn}_full.mp3`（已写入 AGENTS.md 2.5，v1.11）
- 实测：单句 1.37–2.86s，均短于 5 秒镜长 → 音画同步无冲突；时间轴合成用 `adelay + amix(normalize=0) + apad`

## 创作规范（长期）
- **一个 5 秒片段 = 一个主体动作**（不加长，只拆分）
- 每稿定稿前必附"交付前自检清单"（见 EP01/EP02.md 末尾）
- 分镜规范：`docs/分镜规范.md`（v1.0）
- 台词单句 ≤15 字；每集伏笔 ≤1 个；结尾定格未完成动作

## 待确认事项
- 成片预算上限（L3 资金决策）
- 是否已有 DeepSeek 官方 API Key（用户需要用于对照审查剧本）

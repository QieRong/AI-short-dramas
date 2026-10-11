# EP01 准视频（Ken Burns）运镜方案

> **用途**：为 EP01《暗流：消失的千金》10 个镜头规划「静态分镜图 + FFmpeg 运镜」的准视频方案，
> 作为第⑤步（视频生成）的**兜底轨**——在 Agnes 视频队列可用前/不可用时，仍能产出 EP01 成片。
> **上游**：`02_scripts/EP01.md`（镜头定稿）｜ `03_storyboard/EP01_分镜图提示词.md`（分镜图）｜
> `04_assets/scenes/SC_EP01_S*.jpg`（已定稿素材）｜ 配音 `04_assets/audio/AUD_EP01_full.mp3`（50.000s）
> **规范依据**：`docs/准视频方案说明.md` ｜ 抽帧纪律 `AGENTS.md` §3.8 ｜ 命名 `AGENTS.md` §2.5
> **状态**：待用户审查 ｜ **生成日期**：2026-10-11 ｜ **本方案不调用任何 API**

---

## 一、技术底座（现有脚本能力与硬边界）

| 项 | 事实 | 来源 |
|---|---|---|
| 可用运镜 | **仅 4 种**：`in`（推近 1.0→1.25）、`out`（拉远 1.25→1.0）、`left`（左移，1.15 倍下横移）、`right`（右移） | `scripts/kenburns.py` |
| 输出规格 | 720×1280（9:16）、30 fps、H.264、yuv420p | 同上（与 `compose_video.py` 归一化目标一致） |
| 单镜时长 | `--duration`（整数，默认 5）→ **本集全部取 5 秒**，与镜头表一一对应 | 同上 |
| 预处理 | 先放大 2×（1440×2560）再 zoompan，消除缩放抖动/锯齿 | 同上 |
| 运镜力度 | **不可调**——四种运镜的缩放区间与平移速度均为**硬编码常量** | ⚠️ 技术边界（见第六节） |
| 拼接转场 | `compose_video.py` 用 concat demuxer + `-c copy` → **只能硬切**，不支持交叉溶解 | `scripts/compose_video.py` |
| 抽帧 | `kenburns.py` 生成后**自动抽散图**；但**长图/对比图不会自动产出**，需另调 `extract_frames.py` | `kenburns.py` / `extract_frames.py` |

> **结论**：本方案的技术天花板是「**镜头动，画面内容不动**」。
> 它能表达**强调 / 揭示 / 扫视 / 压迫**，**不能表达**任何人物动作（握紧、后仰、按下、灰尘炸开）。

---

## 二、运镜总表（10 镜）

| 镜号 | 时段 | 景别 | 主体动作 | **运镜** | 时长 | 转场（入→出） | 设计理由 |
|---|---|---|---|---|---|---|---|
| **S01** | 00–05 | 特写（手＋U 盘） | 攥紧 U 盘 | **`in`** 推近 | 5.0s | 硬切 → | "攥紧"＝**收紧**，推近同向；把注意力压向掌心的 U 盘 |
| **S02** | 05–10 | 中景·紧构图 | 举枪抵额 | **`in`** 推近 | 5.0s | ← 硬切 → | 向**枪管与额头交界点**逼近，建立压迫感（本镜既定视觉重心） |
| **S03** | 10–15 | 近景 | 枪口挑起下巴 | **`right`** 右移 | 5.0s | ← 硬切 → | 沿**下颌线**（耳下→下巴）横向扫过，跟随被迫抬头的视线方向 |
| **S04** | 15–20 | 大特写 | 瞳孔骤缩 | **`in`** 极缓推近 | 5.0s | ← 硬切 → | "骤缩"无法由静帧表达，**推近是最接近的近似**；心理插切 |
| **S05** | 20–25 | 中景 | 后退一步 | **`out`** 拉远 | 5.0s | ← 硬切 → | "后退"＝两人**距离拉开**，拉远同向；空间向外打开 |
| **S06** | 25–30 | 全景·背影 | 被撞击的瞬间 | **`out`** 拉远 | 5.0s | ← 硬切 → | 全景拉远以**交代被撞现场**（柜体倾倒、灰尘弥漫）；疏离/无助 |
| **S07a** | 30–35 | 中景 | 后退半步 | **`left`** 左移 | 5.0s | ← 硬切 → | 跟随顾承泽的**横向位移**后退；同时**破开** S05–S06 的连续拉远 |
| **S07b** | 35–40 | 特写（手＋扳机） | 扣紧扳机 | **`in`** 推近 | 5.0s | ← 硬切 → | "扣紧"＝**收紧**，手部特写推近，与 S01 形成动作呼应 |
| **S08** | 40–45 | 中景·对称构图 | 枪口直指眉心 | **`out`** 拉远 | 5.0s | ← 硬切 → | 拉远让"两人各占一半"的**对称关系完整呈现**，保留眉心前的空隙 |
| **S09** | 45–50 | 特写（食指） | 食指按下 | **`in`** 最缓推近 | 4.5s + 0.5s 黑 | → **瞬切黑** | 最缓推近压向食指；末尾 0.5s 纯黑＝"按下→黑屏"（见第五节） |

**运镜分布**：`in` × 5 ｜ `out` × 3 ｜ `left` × 1 ｜ `right` × 1 ｜ 合计 10 镜 / 50.0 秒。

### 节奏设计说明

1. **推近用于"收紧/压迫"的镜头**（S01 攥紧、S02 抵额、S04 瞳孔、S07b 扣扳机、S09 按下）
   —— 动作语义都是"**向内收**"，与推近同向，观众体感一致。
2. **拉远用于"距离拉开 / 交代现场"的镜头**（S05 后退、S06 撞柜、S08 对称对峙）
   —— 表达空间打开、处境恶化、关系拉开。
3. **平移只有两处，且都在"顾承泽的位移"上**（S03 挑下巴后的视线跟随、S07a 后退）
   —— 平移在本方案中只用于**跟随视线/横向位移**，符合 `docs/准视频方案说明.md` 的适用场景定义。
4. ⚠️ **S05 与 S06 为相邻的连续 `out`**——这是**有意为之**：形成一组"空间不断打开、她的处境不断恶化"
   的连贯语汇（后退一步 → 撞上柜子）。若不希望相邻重复，备选方案见第七节「待确认 #2」。

---

## 三、逐镜执行命令

输出目录：`04_assets/video/`（依据 `AGENTS.md` §2.4、§2.5，命名 `VID_EP01_S{nn}.mp4`）

```bash
cd scripts

# S01 攥紧 U 盘 —— 推近
python kenburns.py --image ../04_assets/scenes/SC_EP01_S01.jpg \
                   --out  ../04_assets/video/VID_EP01_S01.mp4 --motion in    --duration 5
# S02 举枪抵额 —— 推近
python kenburns.py --image ../04_assets/scenes/SC_EP01_S02.jpg \
                   --out  ../04_assets/video/VID_EP01_S02.mp4 --motion in    --duration 5
# S03 枪口挑下巴 —— 右移（平移类）
python kenburns.py --image ../04_assets/scenes/SC_EP01_S03.jpg \
                   --out  ../04_assets/video/VID_EP01_S03.mp4 --motion right --duration 5
# S04 瞳孔骤缩 —— 推近
python kenburns.py --image ../04_assets/scenes/SC_EP01_S04.jpg \
                   --out  ../04_assets/video/VID_EP01_S04.mp4 --motion in    --duration 5
# S05 后退一步 —— 拉远
python kenburns.py --image ../04_assets/scenes/SC_EP01_S05.jpg \
                   --out  ../04_assets/video/VID_EP01_S05.mp4 --motion out   --duration 5
# S06 被撞击的瞬间 —— 拉远
python kenburns.py --image ../04_assets/scenes/SC_EP01_S06.jpg \
                   --out  ../04_assets/video/VID_EP01_S06.mp4 --motion out   --duration 5
# S07a 后退半步 —— 左移（平移类）
python kenburns.py --image ../04_assets/scenes/SC_EP01_S07a.jpg \
                   --out  ../04_assets/video/VID_EP01_S07a.mp4 --motion left  --duration 5
# S07b 扣紧扳机 —— 推近
python kenburns.py --image ../04_assets/scenes/SC_EP01_S07b.jpg \
                   --out  ../04_assets/video/VID_EP01_S07b.mp4 --motion in   --duration 5
# S08 枪口直指眉心 —— 拉远
python kenburns.py --image ../04_assets/scenes/SC_EP01_S08.jpg \
                   --out  ../04_assets/video/VID_EP01_S08.mp4 --motion out   --duration 5
# S09 食指按下 —— 推近（末段黑屏见第五节）
python kenburns.py --image ../04_assets/scenes/SC_EP01_S09.jpg \
                   --out  ../04_assets/video/VID_EP01_S09.mp4 --motion in    --duration 5
```

### 抽帧纪律补全（`AGENTS.md` §3.8）

`kenburns.py` 自动抽的**只有散图**。按 §3.8.2，**平移类镜必须补产首尾对比图**，推拉类应补产长图：

```bash
# 平移类（S03 / S07a）——必须补首尾对比图（含垂直参考线）
python extract_frames.py ../04_assets/video/VID_EP01_S03.mp4 --force --pan-compare
python extract_frames.py ../04_assets/video/VID_EP01_S07a.mp4 --force --pan-compare

# 推拉类（其余 8 镜）——补长图（运镜概览）
for s in S01 S02 S04 S05 S06 S07b S08 S09; do
  python extract_frames.py ../04_assets/video/VID_EP01_$s.mp4 --force
done
```

> 产物（均已在 `.gitignore` 排除，不入库）：`VID_EP01_S{nn}_frames/`（5 张散图）、
> `*_strip.png`（推拉类概览）、`*_pan_compare.png`（平移类对比）。

---

## 四、与合成链路（第⑦步）的衔接

```
10 个 VID_EP01_S*.mp4（各 5.0s） ─┐
                                  ├─→ compose_video.py ─→ 05_final/EP01_final.mp4
AUD_EP01_full.mp3（50.000s）    ─┘
```

```bash
cd scripts
python compose_video.py \
  --clips ../04_assets/video/VID_EP01_S01.mp4 ../04_assets/video/VID_EP01_S02.mp4 \
          ../04_assets/video/VID_EP01_S03.mp4 ../04_assets/video/VID_EP01_S04.mp4 \
          ../04_assets/video/VID_EP01_S05.mp4 ../04_assets/video/VID_EP01_S06.mp4 \
          ../04_assets/video/VID_EP01_S07a.mp4 ../04_assets/video/VID_EP01_S07b.mp4 \
          ../04_assets/video/VID_EP01_S08.mp4 ../04_assets/video/VID_EP01_S09.mp4 \
  --audio ../04_assets/audio/AUD_EP01_full.mp3 \
  --out ../05_final/EP01_final.mp4
```

**关键事实（已验证）**：
- `concat_clips` 归一化时带 `-an`（**只保留视频流**），音频由 `mux_audio` 单独合入 → 音轨不会因拼接而错位；
- 10 × 5.0s = **50.0s**，与 `AUD_EP01_full.mp3` 的 **50.000s** 精确对齐；
- `mux_audio` 使用 `-shortest`，视频与音轨同为 50.0s → 成片恰为 50.0s。

### 配音时间轴对照（供后续 `EP01_compose_config.json` 使用）

| 台词文件 | 台词 | 角色 | 时长(s) | 落点（镜号 / 秒） |
|---|---|---|---|---|
| `AUD_EP01_S01.mp3` | 还给我。 | 林浅 | 1.54 | S01 / 00 |
| `AUD_EP01_S02.mp3` | 这血，烫手吗？ | 顾承泽 | 2.86 | S02 / 05 |
| `AUD_EP01_S03.mp3` | 沈大小姐死的证据。 | 顾承泽 | 2.69 | S03 / 10 |
| `AUD_EP01_S04.mp3` | —（无台词） | — | — | S04 / 15 |
| `AUD_EP01_S05.mp3` | 你…是谁？ | 林浅 | 1.85 | S05 / 20 |
| `AUD_EP01_S06.mp3` | 别过来！ | 林浅 | 1.37 | S06 / 25 |
| `AUD_EP01_S07a.mp3` | —（无台词） | — | — | S07a / 30 |
| `AUD_EP01_S07b.mp3` | 你疯了。 | 顾承泽 | 1.78 | S07b / 35 |
| `AUD_EP01_S08.mp3` | 最后机会。 | 顾承泽 | 1.97 | S08 / 40 |
| `AUD_EP01_S09.mp3` | —（无台词） | — | — | S09 / 45 |

> **台词占位充裕**：最长句 2.86s，均远短于 5.0s 镜长，不存在挤占冲突（2026-10-11 实测）。

---

## 五、转场方案

### 5.1 结论：**9 个镜间边界全部硬切，结尾用「瞬切黑」**

| 边界 | 转场 | 理由 |
|---|---|---|
| S01→S02 … S08→S09（**9 处**） | **硬切**（hard cut） | ① 本集是**同一空间、连续时间**的单一场景对峙，硬切最贴合紧张节奏，交叉溶解会软化张力；② `compose_video.py` 的 concat + `-c copy` **原生只支持硬切**，零重编码、最稳；③ `docs/EP01.md` 结尾明确要求"**无过渡、无音效延宕**" |
| S09 → 片尾 | **瞬切黑**（非淡出） | 剧本定稿原文：「食指压下 → **黑屏（无过渡、无音效延宕）**」——**刻意不用淡出**，用硬切制造"枪响未响"的悬念断点 |

> ⚠️ 若后续某集需要交叉溶解，须**修改 `compose_video.py`**（改用 `xfade` 滤镜 + 重编码），
> 属脚本级改动。**EP01 不建议启用**（理由见上表）。

### 5.2 S09 末段黑屏的落点（**待确认项 #1**）

剧本要求 S09 在 45–50s 的末尾"瞬间黑屏"，但分镜图阶段**不加黑**（黑屏属剪辑层效果）。
三种落点：

| 方案 | 做法 | 全片时长 | 与现有音轨(50.000s) |
|---|---|---|---|
| (a) | S09 播满 5.0s，之后追加 0.5s 黑 | 50.5s | ❌ 不同步（需补 0.5s 静音或重生成音轨） |
| **(b) ✅ 推荐** | S09 有效画面取 **4.5s**（45.0–49.5），**49.5–50.0 为纯黑** | **50.0s** | ✅ 精确同步，音轨无需改动 |
| (c) | 不加黑，S09 播满 5.0s，黑屏挪到 EP02 开场 | 50.0s | ✅ 但**违背 EP01 结尾设计**（悬念断点缺失） |

**推荐 (b)**——不破坏"总时长 50 秒"的既定约束，也不影响已完成的音轨。

**实现命令（注意：截断必须重编码，不能用 `-c copy`）**：

```bash
# ① S09 准视频（5.0s）已由上节生成
# ② 取前 4.5s —— 必须重编码（`-c copy -t 4.5` 会因关键帧对齐而截出 0 长度）
"C:/Program Files/File Converter/ffmpeg.exe" -y \
  -i ../04_assets/video/VID_EP01_S09.mp4 -t 4.5 \
  -c:v libx264 -preset fast -crf 18 -pix_fmt yuv420p -an \
  -r 30 .tmp_compose/S09_head.mp4

# ③ 生成 0.5s 纯黑（同规格）
"C:/Program Files/File Converter/ffmpeg.exe" -y \
  -f lavfi -i color=c=black:s=720x1280:r=30 -t 0.5 \
  -c:v libx264 -pix_fmt yuv420p .tmp_compose/black_05.mp4

# ④ 末段 = 前 4.5s + 0.5s 黑，替换原 S09 片段后再进 compose
```

---

## 六、动作可替代性分级（**决策就绪信息，不代替用户决策**）

`docs/准视频方案说明.md` §5 已定调：准视频**无法表达人物动作**，关键动作镜仍需真视频。
按此标准对 EP01 逐镜分级：

| 分级 | 定义 | 镜号 | 说明 |
|---|---|---|---|
| **A · 推荐真视频** | 画面的**核心信息就是"动作本身"**，静帧无法承载 | **S04**（瞳孔骤缩）、**S06**（撞柜＋灰尘炸开）、**S09**（食指按下→黑屏） | 这 3 镜用 Ken Burns 只能"近似"——例如 S04 用推近代替瞳孔收缩，语义损失明显 |
| **B · Ken Burns 可近似** | 有动作，但**动作幅度小**或主读点在构图/表情 | **S01**（攥紧）、**S03**（枪口上挑）、**S05**（后退）、**S07a**（后退半步）、**S07b**（扣扳机） | 推近/拉远/平移能给出"同向体感"，观感可接受 |
| **C · Ken Burns 完全够用** | **静势**或纯氛围/对峙镜 | **S02**（枪已抵额）、**S08**（对称对峙） | 画面本就以"静止的张力"为主，运镜即最佳表达 |

**由此得到的「混合方案」切分**（**供参考，待你决定，本方案不擅自降级**）：

```
纯 Ken Burns 出片 ： 10 镜全部（本方案已可直接执行，零 API、零等待）
混合方案         ： 3 镜走真视频（S04 / S06 / S09）+ 7 镜走 Ken Burns
                    → 对应 docs/准视频方案说明.md「每集挑 3-5 个关键镜头用视频 API」
```

> 说明：视频队列当前为 `503 video_queue_full`（容量型限制，非配额）。
> 若明早 07:00 仍不可用，**纯 Ken Burns 版可立刻出片**，不影响项目推进；
> 待队列宽松后，仅需替换 S04 / S06 / S09 三个片段，再重跑一次 `compose_video.py` 即可（其余片段无需重做）。

---

## 七、待确认事项

| # | 事项 | 我的建议 |
|---|---|---|
| **1** | **S09 末段黑屏落点**（(a)/(b)/(c)，见 5.2） | 选 **(b)**：S09 取 4.5s + 0.5s 纯黑，全片精确 50.0s，音轨零改动 |
| **2** | **S05/S06 相邻连续 `out`** 是否接受 | 接受（构成"空间持续打开"的连贯语汇）；备选：S06 改 `in`（推近撞击点），但会弱化"交代现场" |
| **3** | **运镜力度是否需要差异化** | 当前 `kenburns.py` 力度**硬编码**。若需"极缓推近（S04/S09）vs 常规推近（S01）"的差别，需给脚本加 `--zoom-max` / `--speed` 参数（**纯本地改动，不消耗 API**）——**是否要我现在加？** |
| **4** | **抽帧长图/对比图是否补齐** | 建议补（§3.8.2 硬要求，平移类"必开"）；生成准视频时一并执行 |

---

## 八、执行前置条件

| 条件 | 当前状态 |
|---|---|
| 10 张分镜图定稿（`SC_EP01_S*.jpg`） | ✅ 已定稿并入库（10 张 / 320 KB） |
| 整集音轨（`AUD_EP01_full.mp3`，50.000s） | ✅ 已生成 |
| `kenburns.py` 可用 | ✅ FFmpeg 便携版实测可用（`C:\Program Files\File Converter\ffmpeg.exe`） |
| `compose_video.py` 可用 | ✅ 已修复 ffmpeg 解析与 concat 绝对路径，第⑦步首次跑通验证（720×1280 / 30fps / 20s） |
| 字幕文件（`.srt`） | ❌ **未制作**（7 句台词，需在 compose 前生成） |
| API 依赖 | **无** —— 本方案全程本地 |

> 附注：`kenburns.py` 仍**硬编码** File Converter 的 ffmpeg 路径（`extract_frames.py` 同），
> 而 `compose_video.py` 已改为"实测可运行"的动态解析。该不一致属已知技术债，不影响本方案执行。

---

## 九、交付前自检清单

- [ ] 10 镜运镜与 `02_scripts/EP01.md` 的 10 个镜头一一对应（含 7a/7b）
- [ ] 每镜时长 5.0s，合计 50.0s，与 `AUD_EP01_full.mp3` 精确对齐
- [ ] 相邻镜不出现超过两处同向运镜（现状：S05–S06 一处连续 `out`，已注明理由）
- [ ] 平移类（S03/S07a）已补 `--pan-compare` 对比图
- [ ] 推拉类（其余 8 镜）已补 `_strip.png` 长图
- [ ] 所有 MP4 按 §3.8 抽帧到独立目录 `VID_EP01_S{nn}_frames/`，未入库
- [ ] S09 末段黑屏方案已确认（待确认 #1）
- [ ] 字幕 `.srt` 已生成（7 句，与音轨时间轴一致）
- [ ] 成片 `05_final/EP01_final.mp4` = 720×1280 / 30fps / 50.0s

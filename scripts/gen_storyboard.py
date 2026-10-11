"""EP 分镜图批量生成脚本（第④步）。

读 `03_storyboard/EP{nn}_分镜图提示词.md`，逐镜调用 `agnes-image-2.5-flash` 生成分镜图。

用法：
    python gen_storyboard.py --ep 01                 # 生成 EP01 全部镜（已存在的自动跳过）
    python gen_storyboard.py --ep 01 --compress      # 生成后转 1K JPEG 入库（2K 原图归档 _hires/）
    python gen_storyboard.py --ep 01 --dry-run       # 只解析并打印执行计划，不调用 API
    python gen_storyboard.py --ep 01 --only S01,S02  # 只跑指定镜
    python gen_storyboard.py --ep 01 --force         # 忽略已有文件，强制重生成
    python gen_storyboard.py --check                 # 仅检查配置与密钥

设计要点（依据 2026-10-11 用户裁定）：
    1. **断点续跑**：目标文件已存在即跳过（除非 --force）——长批次被中断后可原样重跑。
    2. **--compress**：生成用 2K PNG 保质量；入库前转 1K JPEG（默认质量 85），
       2K 原图归档到 `04_assets/scenes/_hires/`（已加入 .gitignore）。
    3. **特写/大特写镜不传护照图**：护照是半身像，传入会诱导模型保留人脸、弱化"只拍局部"的裁切。
       景别命中「特写 / 大特写」时默认不传参考图；文档的「参考资产」明确写「无」时同样不传。
       （可用 --keep-closeup-refs 关闭该规则。）
    4. 镜与镜之间默认间隔 5 秒，降低触发限流的概率。
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

# 允许直接以脚本方式运行（把 scripts/ 加入模块搜索路径）
sys.path.insert(0, str(Path(__file__).resolve().parent))

from agnes_client import AgnesConfig, AgnesAPIError, has_api_key  # noqa: E402
from agnes_image import generate_image, save_image  # noqa: E402

# ---------------------------------------------------------------- 路径常量

BASE_DIR = Path(__file__).resolve().parent.parent
STORYBOARD_DIR = BASE_DIR / "03_storyboard"
SCENES_DIR = BASE_DIR / "04_assets" / "scenes"
HIRES_DIR = SCENES_DIR / "_hires"
CHARACTERS_DIR = BASE_DIR / "04_assets" / "characters"

# 景别命中这些关键词 → 视为"局部特写镜"，默认不传护照图
CLOSEUP_KEYWORDS = ("特写",)  # "特写" 是 "大特写" 的子串，可一并命中

# ---------------------------------------------------------------- 数据结构


@dataclass
class Shot:
    """单个镜头的解析结果。"""

    sid: str                      # 镜号，如 "S01" / "S07a"
    timecode: str                 # 如 "00–05s"
    shot_size: str                # 景别，如 "特写" / "中景（紧构图）"
    action: str                   # 主体动作
    prompt: str                   # 图像提示词（已合并为单行）
    ref_line: str = ""            # 文档里的「参考资产」原始行
    refs: list[str] = field(default_factory=list)      # 实际要传的护照路径
    ref_note: str = ""            # 参考图决策说明（供打印）
    index: int = 0                # 文档中的出现顺序

    @property
    def is_closeup(self) -> bool:
        return any(k in self.shot_size for k in CLOSEUP_KEYWORDS)


# ---------------------------------------------------------------- 解析


_HEADER_RE = re.compile(
    r"^###\s*镜头\s+(?P<sid>S\d+[ab]?)\s*[｜|]\s*(?P<time>[^｜|]+?)\s*[｜|]\s*"
    r"(?P<size>[^｜|]+?)\s*[｜|]\s*主体动作[:：]\s*(?P<action>.+)$",
    re.MULTILINE,
)
_PROMPT_RE = re.compile(
    r"-\s*\*\*图像提示词\*\*：\s*```[^\n]*\n(?P<body>.*?)```",
    re.DOTALL,
)
_REF_RE = re.compile(r"-\s*\*\*参考资产\*\*：\s*(?P<body>.+)")
_PASSPORT_RE = re.compile(r"`([^`]*_护照\.png)`")


def _clean_prompt(body: str) -> str:
    """把代码块内的多行提示词合并为单行（逐行去缩进后直接拼接）。"""
    lines = []
    for raw in body.splitlines():
        line = raw.strip()
        if not line or line.startswith("```"):
            continue
        lines.append(line)
    return "".join(lines)


def parse_storyboard(md_path: Path) -> list[Shot]:
    """解析分镜图提示词文档，返回按文档顺序排列的镜头列表。"""
    text = md_path.read_text(encoding="utf-8-sig")
    matches = list(_HEADER_RE.finditer(text))
    if not matches:
        raise ValueError(f"未在文档中解析到任何镜头标题：{md_path}")

    shots: list[Shot] = []
    for i, m in enumerate(matches):
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        block = text[start:end]

        pm = _PROMPT_RE.search(block)
        if not pm:
            raise ValueError(f"镜头 {m.group('sid')} 未找到「图像提示词」代码块")
        rm = _REF_RE.search(block)

        shots.append(
            Shot(
                sid=m.group("sid").strip(),
                timecode=m.group("time").strip(),
                shot_size=m.group("size").strip(),
                action=m.group("action").strip(),
                prompt=_clean_prompt(pm.group("body")),
                ref_line=(rm.group("body").strip() if rm else ""),
                index=i,
            )
        )
    return shots


def decide_refs(shot: Shot, keep_closeup_refs: bool = False) -> Shot:
    """决定本镜是否传护照图，并写入 shot.refs / shot.ref_note。"""
    explicit_none = "无" in shot.ref_line
    passports = _PASSPORT_RE.findall(shot.ref_line)

    if explicit_none or not passports:
        shot.refs = []
        shot.ref_note = "不传（文档标注「无」）" if explicit_none else "不传（未指定护照）"
        return shot

    if shot.is_closeup and not keep_closeup_refs:
        shot.refs = []
        shot.ref_note = (
            f"⚠️ 景别={shot.shot_size} → 按「特写镜不传参考图」规则忽略文档指定的 "
            f"{'、'.join(passports)}"
        )
        return shot

    resolved = []
    for name in passports:
        path = CHARACTERS_DIR / name
        if not path.exists():
            raise FileNotFoundError(f"护照文件不存在：{path}")
        resolved.append(str(path))
    shot.refs = resolved
    shot.ref_note = "传 " + "、".join(passports)
    return shot


# ---------------------------------------------------------------- 压缩


def _ffmpeg_qv(quality: int) -> str:
    """把 0-100 的 JPEG 质量折算为 ffmpeg mjpeg 的 -q:v（2 最好，31 最差）。"""
    qv = round((100 - quality) / 3.3)
    return str(max(2, min(31, qv)))


def compress_to_1k(src: Path, dst: Path, quality: int = 85) -> Path:
    """2K PNG → 1K JPEG。优先 Pillow（精确质量），否则回退 ffmpeg。"""
    dst.parent.mkdir(parents=True, exist_ok=True)
    try:
        from PIL import Image  # type: ignore

        img = Image.open(src).convert("RGB")
        w, h = img.size
        scale = 1024 / max(w, h)
        img = img.resize((max(1, round(w * scale)), max(1, round(h * scale))), Image.LANCZOS)
        img.save(dst, "JPEG", quality=quality, optimize=True, progressive=True)
        return dst
    except ImportError:
        pass

    from compose_video import find_ffmpeg  # 复用已修复的解析器（实测可运行才采纳）

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        raise RuntimeError("未找到可用的 ffmpeg，无法压缩")
    cmd = [
        ffmpeg, "-y", "-v", "error",
        "-i", str(src),
        "-vf", "scale=-2:1024",
        "-q:v", _ffmpeg_qv(quality),
        str(dst),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0 or not dst.exists():
        raise RuntimeError(f"ffmpeg 压缩失败：{proc.stderr.strip()[-500:]}")
    return dst


# ---------------------------------------------------------------- 主流程


def target_paths(ep: str, sid: str, compress: bool) -> tuple[Path, Path]:
    """返回 (入库产物路径, 2K 原图归档路径)。"""
    stem = f"SC_EP{ep}_{sid}"
    hires = HIRES_DIR / f"{stem}.png"
    final = SCENES_DIR / (f"{stem}.jpg" if compress else f"{stem}.png")
    return final, hires


def run_one(shot: Shot, config: AgnesConfig, args) -> Path:
    """生成单个镜头，返回产物路径。"""
    final, hires = target_paths(args.ep, shot.sid, args.compress)

    print(f"[生成] {shot.sid}｜{shot.shot_size}｜{shot.action}")
    print(f"       参考图：{shot.ref_note}")
    source = generate_image(
        config,
        shot.prompt,
        size=args.size,
        ratio=args.ratio,
        refs=shot.refs or None,
    )

    if args.compress:
        save_image(source, hires)
        out = compress_to_1k(hires, final, args.jpeg_quality)
        print(f"       → 入库 {out.relative_to(BASE_DIR)}"
              f"（{out.stat().st_size / 1024:.0f} KB）"
              f"｜2K 原图归档 {hires.relative_to(BASE_DIR)}")
    else:
        out = save_image(source, final)
        print(f"       → {out.relative_to(BASE_DIR)}（{out.stat().st_size / 1024:.0f} KB）")
    return out


def print_plan(shots: list[Shot], args) -> None:
    print(f"{'镜号':<6}{'景别':<14}{'主体动作':<12}{'参考图':<8}入库产物")
    print("-" * 78)
    for s in shots:
        final, _ = target_paths(args.ep, s.sid, args.compress)
        status = "已存在·跳过" if final.exists() and not args.force else "待生成"
        n_ref = len(s.refs)
        print(f"{s.sid:<6}{s.shot_size:<14}{s.action:<12}{n_ref:<8}"
              f"{final.name}  [{status}]")
        if s.ref_note.startswith("⚠️"):
            print(f"      {s.ref_note}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="EP 分镜图批量生成（读分镜图提示词文档 → 逐镜出图）"
    )
    parser.add_argument("--ep", default="01", help="集号，如 01（默认 01）")
    parser.add_argument("--md", default=None, help="覆盖默认文档路径")
    parser.add_argument("--size", default="2K", help='图像档位（默认 "2K"）')
    parser.add_argument("--ratio", default="9:16", help='宽高比（默认 "9:16"）')
    parser.add_argument("--compress", action="store_true",
                        help="生成后转 1K JPEG 入库，2K 原图归档 _hires/")
    parser.add_argument("--jpeg-quality", type=int, default=85, help="JPEG 质量（默认 85）")
    parser.add_argument("--only", default=None,
                        help="只跑指定镜号，逗号分隔，如 S01,S02,S07b")
    parser.add_argument("--force", action="store_true", help="已存在也强制重生成")
    parser.add_argument("--dry-run", action="store_true", help="只打印计划，不调用 API")
    parser.add_argument("--keep-closeup-refs", action="store_true",
                        help="关闭「特写/大特写不传护照图」规则")
    parser.add_argument("--delay", type=float, default=5.0,
                        help="镜与镜之间的间隔秒数（默认 5，降低限流风险）")
    parser.add_argument("--keep-going", action="store_true",
                        help="某镜失败时继续后续镜（默认失败即停）")
    parser.add_argument("--check", action="store_true", help="仅检查配置与密钥")
    args = parser.parse_args()

    md_path = Path(args.md) if args.md else STORYBOARD_DIR / f"EP{args.ep}_分镜图提示词.md"
    if not md_path.exists():
        print(f"[错误] 文档不存在：{md_path}", file=sys.stderr)
        return 2

    shots = [decide_refs(s, args.keep_closeup_refs) for s in parse_storyboard(md_path)]

    if args.only:
        wanted = {x.strip().upper() for x in args.only.split(",") if x.strip()}
        shots = [s for s in shots if s.sid.upper() in wanted]
        if not shots:
            print(f"[错误] --only 未匹配到任何镜号：{args.only}", file=sys.stderr)
            return 2

    config = AgnesConfig.load()
    print(f"[文档] {md_path.relative_to(BASE_DIR)}")
    print(f"[配置] 站点={config.site}  base_url={config.base_url}  图像模型={config.image_model}")
    print(f"[参数] size={args.size}  ratio={args.ratio}  compress={args.compress}")
    print(f"[范围] 共 {len(shots)} 镜\n")

    print_plan(shots, args)

    if args.check:
        return 0
    if args.dry_run:
        print("\n[dry-run] 未调用 API。")
        return 0

    if not has_api_key():
        print("\n[错误] 未检测到 AGNES_API_KEY。", file=sys.stderr)
        return 2

    done, skipped, failed = 0, 0, 0
    total = len(shots)
    for i, shot in enumerate(shots, 1):
        final, _ = target_paths(args.ep, shot.sid, args.compress)
        if final.exists() and not args.force:
            skipped += 1
            print(f"\n[{i}/{total}] {shot.sid} 已存在，跳过")
            continue

        print(f"\n[{i}/{total}] ", end="")
        try:
            run_one(shot, config, args)
            done += 1
        except (AgnesAPIError, FileNotFoundError, RuntimeError) as e:
            failed += 1
            print(f"[失败] {shot.sid}：{e}", file=sys.stderr)
            if not args.keep_going:
                print("[中止] 默认失败即停（--keep-going 可继续）。", file=sys.stderr)
                break

        if i < total and args.delay > 0:
            time.sleep(args.delay)

    print(f"\n[汇总] 成功 {done}｜跳过 {skipped}｜失败 {failed}｜总计 {total}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())

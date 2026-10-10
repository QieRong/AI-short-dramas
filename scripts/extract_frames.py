"""视频抽帧器 —— 用 FFmpeg 把 MP4 按固定帧率抽成 PNG，供外部工具审查画面。

依据：AGENTS.md v1.7 §3.8「视频抽帧纪律」

核心约定：
    - 输出目录与视频文件**同级**，名为 `{视频名}_frames/`（独立目录，严禁混帧）
    - 帧图命名 `frame_001.png` 起，三位数编号，保证排序正确
    - 默认 fps=1（每秒 1 帧）；5 秒视频产出 5 张
    - 目录已由 .gitignore 的 `*_frames/` 排除，不入库

双产出（v1.7 新增）：
    - 散图   `{视频名}_frames/frame_001.png...`  —— 单帧细节审查（疤/手势/面部）
    - 长图   `{视频名}_strip.png`                —— 1×N 横向拼接，运镜概览（推拉类）
    - 对比图 `{视频名}_pan_compare.png`          —— 首尾 2 帧并排 + 垂直参考线（平移类）

用法：
    python extract_frames.py ../04_assets/video/VID_EP01_S03.mp4
    python extract_frames.py shot.mp4 --fps 2
    python extract_frames.py shot.mp4 --force             # 覆盖已有帧目录
    python extract_frames.py shot.mp4 --no-strip          # 只抽散图，不出长图
    python extract_frames.py shot.mp4 --pan-compare       # 出首尾对比图（平移类）

作为模块调用：
    from extract_frames import extract_frames
    extract_frames(Path("shot.mp4"))                      # 返回帧图路径列表
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# ffmpeg 便携版路径（项目既定；未入 PATH）
FFMPEG = Path(r"C:\Program Files\File Converter\ffmpeg.exe")

DEFAULT_FPS = 1

# 垂直参考线参数（仅 pan_compare 使用）
REF_LINE_X_RATIO = 0.5    # 线位于画面水平中点
REF_LINE_WIDTH = 4        # 线宽（像素）


def frames_dir_for(video: Path) -> Path:
    """返回视频对应的抽帧目录（同级、以视频名命名的独立目录）。"""
    return video.parent / f"{video.stem}_frames"


def _run_ffmpeg(cmd: list[str]) -> None:
    """执行 ffmpeg，失败抛 RuntimeError。"""
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg 执行失败：\n{result.stderr[-1500:]}")


def extract_frames(
    video: Path,
    fps: int = DEFAULT_FPS,
    force: bool = False,
    ffmpeg: Path = FFMPEG,
) -> list[Path]:
    """把视频按 fps 抽帧到独立目录，返回生成的帧图路径列表（已排序）。

    参数：
        video  : 输入 MP4 路径
        fps    : 抽帧频率，默认 1（每秒 1 帧）
        force  : 为 True 时删除并重建已存在的帧目录
        ffmpeg : ffmpeg 可执行文件路径

    异常：
        FileNotFoundError : 视频或 ffmpeg 不存在
        RuntimeError      : ffmpeg 执行失败
    """
    video = Path(video).resolve()
    if not video.is_file():
        raise FileNotFoundError(f"找不到视频文件：{video}")
    if not Path(ffmpeg).exists():
        raise FileNotFoundError(f"找不到 ffmpeg：{ffmpeg}")

    out_dir = frames_dir_for(video)

    if out_dir.exists():
        if not force:
            raise FileExistsError(
                f"帧目录已存在：{out_dir}\n"
                f"如需覆盖请加 --force"
            )
        shutil.rmtree(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _run_ffmpeg([
        str(ffmpeg), "-y",
        "-i", str(video),
        "-vf", f"fps={fps}",
        str(out_dir / "frame_%03d.png"),
    ])

    frames = sorted(out_dir.glob("frame_*.png"))
    if not frames:
        raise RuntimeError("ffmpeg 执行成功但未产出任何帧图")
    return frames


def make_strip(
    frames: list[Path],
    ffmpeg: Path = FFMPEG,
) -> Path:
    """把 N 张等尺寸帧图横向拼成 1 张长图，输出与帧目录同级。

    输出名：`{视频名}_strip.png`（视频名 = 帧目录名去掉 `_frames` 后缀）。
    适用：推拉类运镜（1×N 横向，时序渐变一眼可见）。
    """
    if len(frames) < 2:
        raise ValueError("至少需要 2 帧才能拼接长图")
    if not Path(ffmpeg).exists():
        raise FileNotFoundError(f"找不到 ffmpeg：{ffmpeg}")

    frames = [Path(f).resolve() for f in frames]
    out = _strip_path_for(frames)

    cmd = [str(ffmpeg), "-y"]
    for f in frames:
        cmd += ["-i", str(f)]
    cmd += [
        "-filter_complex", f"hstack=inputs={len(frames)}",
        str(out),
    ]
    _run_ffmpeg(cmd)
    return out


def make_pan_compare(
    frames: list[Path],
    ffmpeg: Path = FFMPEG,
) -> Path:
    """把首尾 2 帧并排拼接，并在**两帧各画一条垂直参考线**，输出同级目录。

    输出名：`{视频名}_pan_compare.png`。
    适用：平移类运镜（left/right）——首尾帧并排可直接对比背景位移，
    垂直参考线提供跨帧可对齐的固定参照，缓解「缺少固定参照物」问题。
    """
    if len(frames) < 2:
        raise ValueError("至少需要 2 帧才能生成对比图")
    if not Path(ffmpeg).exists():
        raise FileNotFoundError(f"找不到 ffmpeg：{ffmpeg}")

    first, last = Path(frames[0]).resolve(), Path(frames[-1]).resolve()
    out = _pan_compare_path_for(frames)

    # 对每帧叠加垂直红线（drawbox），再 hstack 并排
    line = (
        f"drawbox=x=iw*{REF_LINE_X_RATIO}-{REF_LINE_WIDTH//2}"
        f":y=0:w={REF_LINE_WIDTH}:h=ih:color=red@0.9:t=fill"
    )
    filter_complex = (
        f"[0:v]{line}[a];"
        f"[1:v]{line}[b];"
        f"[a][b]hstack=inputs=2"
    )
    cmd = [
        str(ffmpeg), "-y",
        "-i", str(first),
        "-i", str(last),
        "-filter_complex", filter_complex,
        str(out),
    ]
    _run_ffmpeg(cmd)
    return out


def _strip_path_for(frames: list[Path]) -> Path:
    """由帧图路径推导长图输出路径：{视频名}_strip.png（与帧目录同级）。"""
    frames_dir = Path(frames[0]).resolve().parent     # .../{视频名}_frames
    name = frames_dir.name.removesuffix("_frames")
    return frames_dir.parent / f"{name}_strip.png"


def _pan_compare_path_for(frames: list[Path]) -> Path:
    """由帧图路径推导对比图输出路径：{视频名}_pan_compare.png。"""
    frames_dir = Path(frames[0]).resolve().parent
    name = frames_dir.name.removesuffix("_frames")
    return frames_dir.parent / f"{name}_pan_compare.png"


def main() -> int:
    ap = argparse.ArgumentParser(description="视频抽帧（AGENTS.md §3.8）")
    ap.add_argument("video", help="输入 MP4 路径")
    ap.add_argument("--fps", type=int, default=DEFAULT_FPS,
                    help=f"抽帧频率，默认 {DEFAULT_FPS}（每秒 1 帧）")
    ap.add_argument("--force", action="store_true",
                    help="覆盖已存在的帧目录")
    ap.add_argument("--no-strip", action="store_true",
                    help="不生成 1×N 横向长图（默认生成）")
    ap.add_argument("--pan-compare", action="store_true",
                    help="额外生成首尾 2 帧对比图 + 垂直参考线（平移类运镜）")
    args = ap.parse_args()

    if args.fps <= 0:
        print("[错误] --fps 必须为正整数", file=sys.stderr)
        return 2

    try:
        frames = extract_frames(
            Path(args.video), fps=args.fps, force=args.force,
        )
    except FileExistsError as e:
        print(f"[跳过] {e}", file=sys.stderr)
        return 3
    except (FileNotFoundError, RuntimeError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    out_dir = frames[0].parent
    print(f"[散图] {len(frames)} 张 → {out_dir}")
    print(f"       文件：{frames[0].name} ~ {frames[-1].name}")

    # 长图（默认产出）
    if not args.no_strip:
        try:
            strip = make_strip(frames)
            print(f"[长图] → {strip}")
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            print(f"[长图] 失败（不阻塞）：{e}", file=sys.stderr)

    # 平移对比图（按需）
    if args.pan_compare:
        try:
            cmp_path = make_pan_compare(frames)
            print(f"[对比图] → {cmp_path}")
        except (FileNotFoundError, RuntimeError, ValueError) as e:
            print(f"[对比图] 失败（不阻塞）：{e}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())

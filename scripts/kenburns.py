"""准视频生成器 —— 用静态图 + FFmpeg Ken Burns 运镜生成动态片段。

背景：Agnes 视频 API 免费层限流严重，作为备选方案，用 FFmpeg 的
      zoompan 滤镜为静态分镜图/角色图添加推拉摇移，生成"准视频"。

支持 4 种运镜：
    in    : 缓慢推近（zoom in）—— 强调/逼近情绪
    out   : 缓慢拉远（zoom out）—— 揭示环境
    left  : 向左平移（pan left）
    right : 向右平移（pan right）

用法：
    python kenburns.py --image ../04_assets/characters/林浅_护照.png \
                       --out ../04_assets/video/_test_kenburns_in.mp4 \
                       --motion in --duration 5
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

from extract_frames import extract_frames

FFMPEG = Path(r"C:\Program Files\File Converter\ffmpeg.exe")

W, H = 720, 1280          # 竖屏输出
FPS = 30


def _auto_extract(video: Path) -> None:
    """准视频生成后按 AGENTS.md §3.8 自动抽帧；失败不阻塞主流程。"""
    try:
        frames = extract_frames(video, force=True)
        print(f"[抽帧] {len(frames)} 张 → {frames[0].parent}")
    except (FileNotFoundError, RuntimeError, OSError) as e:
        print(f"[抽帧] 失败（不阻塞主流程）：{e}", file=sys.stderr)


def build_filter(motion: str, duration: int) -> str:
    """构造 zoompan 滤镜表达式。

    输入先放大到 2x 再 zoompan，避免缩放过程中的抖动/锯齿。
    d = 帧数 = fps * duration；s = 输出尺寸。
    z  随帧推进在 [z0, z1] 间线性变化；x/y 决定取样窗口位置。
    """
    frames = FPS * duration
    # 预放大系数，缓解 zoompan 的缩放抖动
    pre = 2

    if motion == "in":
        z = "min(1.0+0.0015*on,1.25)"          # 1.0 → 1.25
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    elif motion == "out":
        z = "max(1.25-0.0015*on,1.0)"          # 1.25 → 1.0
        x, y = "(iw-iw/zoom)/2", "(ih-ih/zoom)/2"
    elif motion == "left":
        z = "1.15"
        x, y = "(iw-iw/zoom)*on/{f}".format(f=frames), "(ih-ih/zoom)/2"
    elif motion == "right":
        z = "1.15"
        x, y = "(iw-iw/zoom)*(1-on/{f})".format(f=frames), "(ih-ih/zoom)/2"
    else:
        raise ValueError(f"未知运镜: {motion}")

    return (
        f"scale={W*pre}:{H*pre},"
        f"zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s={W}x{H}:fps={FPS},"
        f"format=yuv420p"
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--image", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--motion", default="in",
                    choices=["in", "out", "left", "right"])
    ap.add_argument("--duration", type=int, default=5)
    args = ap.parse_args()

    src = Path(args.image)
    if not src.exists():
        print(f"[错误] 找不到图片 {src}", file=sys.stderr)
        return 2
    if not FFMPEG.exists():
        print(f"[错误] 找不到 ffmpeg {FFMPEG}", file=sys.stderr)
        return 2

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)

    vf = build_filter(args.motion, args.duration)
    cmd = [
        str(FFMPEG), "-y",
        "-loop", "1", "-i", str(src),
        "-t", str(args.duration),
        "-vf", vf,
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
        "-r", str(FPS),
        str(out),
    ]
    print("[ffmpeg] 生成中...")
    print("  " + " ".join(f'"{c}"' if " " in c else c for c in cmd))
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        print("[错误] ffmpeg 失败：", file=sys.stderr)
        print(r.stderr[-1500:], file=sys.stderr)
        return 1
    size = out.stat().st_size
    print(f"[完成] {out}  ({size/1024:.0f} KB, {args.duration}s, {args.motion})")
    _auto_extract(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""FFmpeg 合成脚本。

职责单一：把视频片段、配音、字幕合成为成片。

自动检测本机 ffmpeg（PATH 或已知便携路径）。

用法：
    python compose_video.py --check                    # 检查 ffmpeg 可用性
    python compose_video.py --clips a.mp4 b.mp4 --out ../05_final/output.mp4
    python compose_video.py --clips *.mp4 --audio line.mp3 --out output.mp4 --subtitle sub.srt
"""

from __future__ import annotations

import argparse
import glob
import os
import shutil
import subprocess
import sys
from pathlib import Path

# 已知的便携 ffmpeg 路径（本机实测可运行）
KNOWN_FFMPEG_PATHS = [
    r"C:\Program Files\File Converter\ffmpeg.exe",
    r"D:\Program Files\JiJiDown\OrderEXE\ffmpeg.exe",
]


def _winget_candidates(tool: str) -> list[str]:
    """枚举 WinGet 安装的 ffmpeg/ffprobe 真实二进制路径。

    背景：WinGet 会在 ...\\WinGet\\Links\\ 生成别名桩，本机这些桩是 0 字节
    且不可执行（WinError 193）；真实二进制位于 Packages\\Gyan.FFmpeg*\\
    ffmpeg-*\\bin\\ 下。此处按版本号倒序枚举，供候选链使用。
    """
    local = os.environ.get("LOCALAPPDATA")
    if not local:
        return []
    pattern = str(
        Path(local) / "Microsoft" / "WinGet" / "Packages"
        / "Gyan.FFmpeg*" / "ffmpeg-*" / "bin" / f"{tool}.exe"
    )
    return sorted(glob.glob(pattern), reverse=True)


def _runs(path: str) -> bool:
    """验证可执行文件真能运行（能跑出 -version 输出）。

    背景：WinGet 的 App 执行别名桩（...\\WinGet\\Links\\ffmpeg.exe）是 0 字节文件，
    shutil.which 能命中，但执行时报 WinError 193。若只用 Path.exists() 判断，
    会把这类桩误判为可用，导致合成静默失败。故以「能否跑出版本信息」为唯一判据。
    """
    try:
        result = subprocess.run(
            [path, "-version"], capture_output=True, text=True, timeout=15,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool((result.stdout or "").strip())


def find_ffmpeg() -> str | None:
    """定位可用的 ffmpeg：优先 PATH，其次已知便携路径。

    每个候选都必须通过 _runs() 实测，以跳过 PATH 中的零字节别名桩。
    """
    candidates: list[str] = []
    found = shutil.which("ffmpeg")
    if found:
        candidates.append(found)
    candidates.extend(KNOWN_FFMPEG_PATHS)
    candidates.extend(_winget_candidates("ffmpeg"))
    for path in candidates:
        if Path(path).exists() and _runs(path):
            return path
    return None


def find_ffprobe() -> str | None:
    """定位可用的 ffprobe（PATH → 便携 ffmpeg 同目录 → WinGet 真实安装）。"""
    candidates: list[str] = []
    found = shutil.which("ffprobe")
    if found:
        candidates.append(found)
    candidates.extend(str(Path(p).parent / "ffprobe.exe") for p in KNOWN_FFMPEG_PATHS)
    candidates.extend(_winget_candidates("ffprobe"))
    for path in candidates:
        if Path(path).exists() and _runs(path):
            return path
    return None


def concat_clips(ffmpeg: str, clips: list[Path], out: Path, tmp_dir: Path) -> None:
    """拼接多个视频片段（先统一编码再 concat）。"""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    norm_dir = tmp_dir / "norm"
    norm_dir.mkdir(exist_ok=True)

    # 统一尺寸/编码/帧率，确保 concat 稳定
    normalized = []
    for i, clip in enumerate(clips):
        target = norm_dir / f"n{i:03d}.mp4"
        subprocess.run(
            [ffmpeg, "-y", "-i", str(clip),
             "-vf", "scale=720:1280:force_original_aspect_ratio=decrease,pad=720:1280:(ow-iw)/2:(oh-ih)/2",
             "-r", "30", "-c:v", "libx264", "-preset", "fast", "-crf", "23",
             "-an", str(target)],
            check=True, capture_output=True,
        )
        normalized.append(target)

    # 必须写绝对路径：ffmpeg 的 concat 解析器以「清单文件所在目录」为基准，
    # 相对路径会被二次拼接而找不到文件（.tmp_compose/.tmp_compose/...）。
    list_file = tmp_dir / "concat.txt"
    list_file.write_text(
        "\n".join(f"file '{c.resolve().as_posix()}'" for c in normalized),
        encoding="utf-8",
    )

    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [ffmpeg, "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
         "-c", "copy", str(out)],
        check=True, capture_output=True,
    )


def mux_audio(ffmpeg: str, video: Path, audio: Path, out: Path) -> None:
    """为视频合入配音音轨。"""
    subprocess.run(
        [ffmpeg, "-y", "-i", str(video), "-i", str(audio),
         "-c:v", "copy", "-c:a", "aac", "-shortest", str(out)],
        check=True, capture_output=True,
    )


def burn_subtitle(ffmpeg: str, video: Path, subtitle: Path, out: Path) -> None:
    """烧录字幕。"""
    sub_escaped = str(subtitle).replace("\\", "/").replace(":", "\\:")
    subprocess.run(
        [ffmpeg, "-y", "-i", str(video),
         "-vf", f"subtitles='{sub_escaped}'",
         "-c:a", "copy", str(out)],
        check=True, capture_output=True,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="FFmpeg 合成")
    parser.add_argument("--clips", nargs="+", help="视频片段路径（按顺序）")
    parser.add_argument("--audio", help="配音音轨")
    parser.add_argument("--subtitle", help="字幕文件 (.srt)")
    parser.add_argument("--out", help="输出文件")
    parser.add_argument("--tmp", default=".tmp_compose", help="临时目录")
    parser.add_argument("--check", action="store_true", help="检查 ffmpeg")
    args = parser.parse_args()

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print("[错误] 未找到 ffmpeg。请安装并加入 PATH。", file=sys.stderr)
        return 2

    print(f"[ffmpeg] {ffmpeg}")
    if args.check:
        ver = subprocess.run([ffmpeg, "-version"], capture_output=True, text=True)
        print(ver.stdout.splitlines()[0] if ver.stdout else "(版本未知)")
        probe = find_ffprobe()
        print(f"[ffprobe] {probe or '未找到'}")
        return 0

    if not args.clips or not args.out:
        print("[错误] 需提供 --clips 和 --out", file=sys.stderr)
        return 2

    clips = [Path(c) for c in args.clips]
    missing = [c for c in clips if not c.exists()]
    if missing:
        print(f"[错误] 片段不存在: {missing}", file=sys.stderr)
        return 2

    out = Path(args.out)
    tmp = Path(args.tmp)

    print(f"[合成] 拼接 {len(clips)} 个片段...")
    try:
        concat_clips(ffmpeg, clips, out, tmp)
        current = out

        if args.audio:
            audio_path = Path(args.audio)
            if not audio_path.exists():
                print(f"[错误] 音轨不存在: {audio_path}", file=sys.stderr)
                return 2
            merged = out.with_name(out.stem + "_audio.mp4")
            print("[合成] 合入配音...")
            mux_audio(ffmpeg, current, audio_path, merged)
            current = merged

        if args.subtitle:
            sub_path = Path(args.subtitle)
            if not sub_path.exists():
                print(f"[错误] 字幕不存在: {sub_path}", file=sys.stderr)
                return 2
            burned = out.with_name(out.stem + "_final.mp4")
            print("[合成] 烧录字幕...")
            burn_subtitle(ffmpeg, current, sub_path, burned)
            current = burned

        if current != out:
            current.replace(out)
    except subprocess.CalledProcessError as e:
        print(f"[错误] ffmpeg 执行失败: {e.stderr.decode('utf-8', 'replace')[:500]}", file=sys.stderr)
        return 1

    print(f"[完成] 成片已保存到 {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

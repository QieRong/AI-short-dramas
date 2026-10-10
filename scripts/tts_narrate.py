"""Edge-TTS 配音脚本。

职责单一：把台词文本合成为语音文件。
完全免费（微软 Edge 在线 TTS），无需任何 API Key。

依赖：pip install edge-tts
用法：
    python tts_narrate.py --text "你好，世界" --out ../04_assets/audio/line01.mp3
    python tts_narrate.py --text-file lines.txt --out line.mp3 --voice zh-CN-YunxiNeural
    python tts_narrate.py --list-voices        # 列出中文音色
"""

from __future__ import annotations

import argparse
import asyncio
import subprocess
import sys
from pathlib import Path


def ensure_edge_tts() -> bool:
    """检查 edge-tts 是否可用。"""
    try:
        subprocess.run(
            [sys.executable, "-m", "edge_tts", "--version"],
            capture_output=True, check=True,
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError):
        return False


def synthesize(text: str, out_path: Path, voice: str, rate: str = "+0%") -> Path:
    """调用 edge-tts 生成语音。"""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "edge_tts",
        "--text", text,
        "--voice", voice,
        "--rate", rate,
        "--write-media", str(out_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True)
    return out_path


def list_chinese_voices() -> None:
    """列出可用中文音色。"""
    result = subprocess.run(
        [sys.executable, "-m", "edge_tts", "--list-voices"],
        capture_output=True, text=True,
    )
    for line in result.stdout.splitlines():
        if "zh-CN" in line:
            print(line)


def main() -> int:
    parser = argparse.ArgumentParser(description="Edge-TTS 配音")
    parser.add_argument("--text", help="台词文本")
    parser.add_argument("--text-file", help="从文件读取台词")
    parser.add_argument("--out", help="输出音频路径")
    parser.add_argument("--voice", default="zh-CN-YunxiNeural", help="音色")
    parser.add_argument("--rate", default="+0%", help="语速")
    parser.add_argument("--list-voices", action="store_true", help="列出中文音色")
    args = parser.parse_args()

    if not ensure_edge_tts():
        print(
            "[错误] 未安装 edge-tts。请执行：pip install edge-tts",
            file=sys.stderr,
        )
        return 2

    if args.list_voices:
        list_chinese_voices()
        return 0

    text = args.text
    if args.text_file:
        text = Path(args.text_file).read_text(encoding="utf-8")
    if not text or not args.out:
        print("[错误] 需提供 --text/--text-file 和 --out", file=sys.stderr)
        return 2

    dest = synthesize(text.strip(), Path(args.out), args.voice, args.rate)
    print(f"[完成] 配音已保存到 {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

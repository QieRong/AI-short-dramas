"""Agnes 适配层环境自检。

一次性检查：配置、密钥、三个模型端点连通性、Edge-TTS、FFmpeg。
不产生任何生成任务，零成本（仅做轻量连通性探测）。

用法：
    python check_env.py
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from agnes_client import AgnesConfig, has_api_key, key_source, request_json, AgnesAPIError
from compose_video import find_ffmpeg, find_ffprobe


def ok(msg: str) -> None:
    print(f"  [OK]   {msg}")


def warn(msg: str) -> None:
    print(f"  [警告] {msg}")


def fail(msg: str) -> None:
    print(f"  [缺失] {msg}")


def check_config() -> AgnesConfig | None:
    print("\n[1/5] 配置加载")
    try:
        config = AgnesConfig.load()
        ok(f"站点={config.site}  base_url={config.base_url}")
        ok(f"模型: 文本={config.text_model} 图像={config.image_model} 视频={config.video_model}")
        return config
    except Exception as e:
        fail(f"配置加载失败: {e}")
        return None


def check_key() -> bool:
    print("\n[2/5] API 密钥")
    if has_api_key():
        ok(f"密钥已就绪，来源：{key_source()}（内容不显示）")
        return True
    fail(
        "未检测到 AGNES_API_KEY。请选一种方式：\n"
        "         方式1（推荐）：cmd 执行 setx AGNES_API_KEY \"你的密钥\"，重启 WorkBuddy\n"
        "         方式2：编辑 scripts/.env 填入 AGNES_API_KEY=你的密钥"
    )
    return False


def check_endpoints(config: AgnesConfig) -> None:
    print("\n[3/5] 模型端点连通性")
    if not has_api_key():
        warn("跳过（无密钥）")
        return

    # 文本模型：最小 token 请求探测
    try:
        result = request_json(
            config, "POST", "/chat/completions",
            payload={
                "model": config.text_model,
                "messages": [{"role": "user", "content": "hi"}],
                "max_tokens": 1,
            },
            timeout=60, max_retries=1,
        )
        ok(f"文本模型 {config.text_model} 可达")
    except AgnesAPIError as e:
        fail(f"文本模型: {str(e)[:200]}")

    # 图像与视频端点：仅验证端点存在（不实际生成，避免消耗）
    warn("图像/视频端点需实际调用验证，此处不触发以节省额度")


def check_edge_tts() -> None:
    print("\n[4/5] Edge-TTS 配音")
    try:
        subprocess.run(
            [sys.executable, "-m", "edge_tts", "--version"],
            capture_output=True, check=True,
        )
        ok("edge-tts 已安装")
    except (subprocess.CalledProcessError, FileNotFoundError):
        fail("未安装 edge-tts。请执行：pip install edge-tts")


def check_ffmpeg() -> None:
    print("\n[5/5] FFmpeg")
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        ok(f"ffmpeg: {ffmpeg}")
        probe = find_ffprobe()
        if probe:
            ok(f"ffprobe: {probe}")
        else:
            warn("未找到 ffprobe（部分功能可能受限）")
    else:
        fail("未找到 ffmpeg。请安装并加入 PATH")


def main() -> int:
    print("=" * 60)
    print("Agnes 适配层环境自检")
    print("=" * 60)

    config = check_config()
    key_ok = check_key()
    if config:
        check_endpoints(config)
    check_edge_tts()
    check_ffmpeg()

    print("\n" + "=" * 60)
    print("自检完成")
    print("=" * 60)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Agnes 视频模型适配脚本（依据官方文档修正版）。

官方文档：https://wiki.agnes-ai.com/zh-Hans/docs/agnes-video-25-flash

正确 schema（此前 t2v/i2v/duration/720x1280 均为错误推测）：
    POST /v1/videos
    {
      "model": "agnes-video-2.5-flash",
      "prompt": "...",
      "mode": "text" | "keyframe" | "reference",   # 必填
      "seconds": "5",          # 字符串，4-12，默认 "5"
      "size": "720P",          # Flash 固定 "720P"
      "aspect_ratio": "9:16",  # 竖屏；输出 720x1280
      "n": 1,
      # mode=keyframe: first_frame / last_frame（至少一个）
      # mode=reference: images[](≤5) / audios[](≤3)
      # mode=text: 不允许任何媒体字段
    }

查询任务（推荐）：
    GET /agnesapi?video_id=<VIDEO_ID>&model_name=agnes-video-2.5-flash
    （纯 video_id 查询仅适用于 mode:"text"）

    video_id 用于查询；返回中的 id / task_id 是任务 ID。

最大单点风险是免费层的 429 限流。规避手段：
    1) 每次「创建任务」之间强制间隔 CREATE_INTERVAL 秒（默认取配置 create_interval）；
    2) 429 时按 15s/30s 退避重试，而不是立即失败。

用法：
    python agnes_video.py --prompt "..." --out ../04_assets/video/ep01_s1.mp4
    python agnes_video.py --prompt "..." --image-url "https://..." --out shot.mp4   # img2video（reference）
    python agnes_video.py --prompt "..." --first-frame-url "https://..." --out shot.mp4  # keyframe
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from agnes_client import (
    AgnesConfig,
    AgnesAPIError,
    download_file,
    has_api_key,
    request_json,
)

_STATE_PATH = Path(__file__).resolve().parent / ".video_throttle.json"


def _respect_create_interval(config: AgnesConfig) -> None:
    """强制两次「创建任务」之间至少间隔 create_interval 秒。

    状态写在 scripts/.video_throttle.json（已加入 .gitignore）。
    """
    interval = config.video_create_interval
    now = time.time()
    last = 0.0
    if _STATE_PATH.exists():
        try:
            last = float(json.loads(_STATE_PATH.read_text(encoding="utf-8")).get("last_create", 0))
        except (ValueError, OSError):
            last = 0.0
    wait = interval - (now - last)
    if wait > 0:
        print(f"[节流] 距上次创建任务不足 {interval}s，等待 {wait:.0f}s ...")
        time.sleep(wait)
    _STATE_PATH.write_text(json.dumps({"last_create": time.time()}), encoding="utf-8")


def create_video_task(
    config: AgnesConfig,
    prompt: str,
    mode: str = "text",
    seconds: str | None = None,
    size: str | None = None,
    aspect_ratio: str | None = None,
    first_frame: str | None = None,
    last_frame: str | None = None,
    images: list[str] | None = None,
    audios: list[str] | None = None,
) -> tuple[str, str]:
    """创建视频任务，返回 (video_id, task_id)。

    mode 合法值（实测确认）：text / keyframe / reference
        - reference 缺 images/audios/videos 时会返回 400 invalid_request（说明 mode 本身合法）
    """
    payload: dict = {
        "model": config.video_model,
        "prompt": prompt,
        "mode": mode,
        "seconds": str(seconds if seconds is not None else config.video_seconds),
        "size": size or config.video_size,
        "aspect_ratio": aspect_ratio or config.video_aspect_ratio,
        "n": 1,
    }
    if mode == "keyframe":
        if first_frame:
            payload["first_frame"] = first_frame
        if last_frame:
            payload["last_frame"] = last_frame
    elif mode == "reference":
        if images:
            payload["images"] = images
        if audios:
            payload["audios"] = audios

    _respect_create_interval(config)
    result = request_json(config, "POST", "/videos", payload=payload, timeout=120)

    video_id = str(result.get("video_id", "") or result.get("id", ""))
    task_id = str(result.get("id", "") or result.get("task_id", "") or video_id)
    if not video_id:
        raise RuntimeError(f"未找到 video_id 字段: {result}")
    return video_id, task_id


def poll_video_task(config: AgnesConfig, video_id: str) -> str:
    """轮询任务直到完成，返回视频 URL。

    使用官方推荐的 video_id + model_name 查询方式（全模式通用）。
    """
    endpoint = f"/agnesapi?video_id={video_id}&model_name={config.video_model}"
    max_poll = config.video_max_poll_attempts
    interval = config.video_poll_interval
    for attempt in range(1, max_poll + 1):
        result = request_json(config, "GET", endpoint, timeout=60, retry_on_429=False)
        status = str(result.get("status", "")).lower()
        progress = result.get("progress", "")
        print(f"  轮询 {attempt}/{max_poll}: status={status or '未知'}"
              + (f" progress={progress}" if progress != "" else ""))

        if status in ("succeeded", "success", "completed", "done"):
            return _extract_url(result)

        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"任务失败: {result.get('error', result)}")

        time.sleep(interval)

    raise TimeoutError(f"轮询超时（{max_poll * interval} 秒）")


def _extract_url(result: dict) -> str:
    """从完成的任务响应中提取视频 URL。"""
    for key in ("url", "video_url", "output"):
        if key in result:
            value = result[key]
            if isinstance(value, list) and value:
                value = value[0]
            if isinstance(value, dict):
                value = value.get("url", "")
            if value:
                return str(value)
    # 兜底：深挖可能嵌套
    raise RuntimeError(f"任务完成但未找到视频 URL: {result}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Agnes 视频生成（官方 schema）")
    parser.add_argument("--prompt", help="视频提示词")
    parser.add_argument("--out", help="输出视频路径")
    parser.add_argument("--mode", default="text",
                        choices=["text", "keyframe", "reference"], help="生成模式")
    parser.add_argument("--seconds", default=None, help="时长 4-12（字符串），默认取配置")
    parser.add_argument("--aspect-ratio", default=None, help="画幅，默认取配置（9:16）")
    parser.add_argument("--image-url", action="append",
                        help="参考图 URL（mode=reference，可多次）")
    parser.add_argument("--first-frame-url", help="首帧 URL（mode=keyframe）")
    parser.add_argument("--last-frame-url", help="尾帧 URL（mode=keyframe）")
    parser.add_argument("--check", action="store_true", help="仅检查配置与密钥")
    args = parser.parse_args()

    config = AgnesConfig.load()
    print(f"[配置] 站点={config.site}  base_url={config.base_url}")
    print(f"[配置] 视频模型={config.video_model}")

    if not has_api_key():
        print("[错误] 未检测到 AGNES_API_KEY。", file=sys.stderr)
        return 2
    print("[密钥] 已就绪")

    if args.check:
        return 0
    if not args.prompt or not args.out:
        print("[错误] 需提供 --prompt 和 --out", file=sys.stderr)
        return 2

    mode = args.mode
    if args.first_frame_url or args.last_frame_url:
        mode = "keyframe"
    elif args.image_url:
        mode = "reference"

    print(f"[调用] 创建视频任务（mode={mode}, seconds={args.seconds}）...")
    try:
        video_id, task_id = create_video_task(
            config, args.prompt, mode=mode, seconds=args.seconds,
            aspect_ratio=args.aspect_ratio,
            first_frame=args.first_frame_url, last_frame=args.last_frame_url,
            images=args.image_url,
        )
        print(f"[任务] video_id={video_id}")
        print("[轮询] 等待生成完成...")
        video_url = poll_video_task(config, video_id)
        print("[完成] 视频 URL 已获取")
    except (AgnesAPIError, RuntimeError, TimeoutError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    dest = download_file(video_url, Path(args.out))
    print(f"[完成] 已保存到 {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

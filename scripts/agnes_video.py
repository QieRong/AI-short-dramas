"""Agnes 视频模型适配脚本。

职责单一：调用 agnes-video-2.5-flash 创建视频生成任务，轮询状态，
完成后下载视频到本地。

流程（参照官方文档）：POST /v1/videos 创建任务 -> 轮询 -> 下载。

用法：
    python agnes_video.py --prompt "雨夜街头，主角转身" --out ../04_assets/video/ep01_shot1.mp4
    python agnes_video.py --image ../04_assets/characters/hero.png --prompt "轻微点头" --out shot.mp4
    python agnes_video.py --check
"""

from __future__ import annotations

import argparse
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

# 轮询配置
POLL_INTERVAL = 10
MAX_POLL = 60


def create_video_task(
    config: AgnesConfig,
    prompt: str,
    size: str,
    duration: int,
    image_url: str | None = None,
) -> str:
    """创建视频生成任务，返回 task id。"""
    payload: dict = {
        "model": config.video_model,
        "prompt": prompt,
        "size": size,
        "duration": duration,
    }
    if image_url:
        payload["image"] = image_url  # 图生视频

    result = request_json(config, "POST", "/videos", payload=payload, timeout=120)

    for key in ("id", "task_id", "request_id"):
        if key in result:
            return str(result[key])
    raise RuntimeError(f"未找到 task id 字段: {result}")


def poll_video_task(config: AgnesConfig, task_id: str) -> str:
    """轮询任务直到完成，返回视频 URL。"""
    for attempt in range(1, MAX_POLL + 1):
        result = request_json(config, "GET", f"/videos/{task_id}", timeout=60)
        status = str(result.get("status", "")).lower()

        print(f"  轮询 {attempt}/{MAX_POLL}: status={status or '未知'}")

        if status in ("succeeded", "success", "completed", "done"):
            for key in ("url", "video_url", "output"):
                if key in result:
                    value = result[key]
                    if isinstance(value, list) and value:
                        value = value[0]
                    if isinstance(value, dict):
                        value = value.get("url", "")
                    return str(value)
            raise RuntimeError(f"任务完成但未找到视频 URL: {result}")

        if status in ("failed", "error", "cancelled"):
            raise RuntimeError(f"任务失败: {result.get('error', result)}")

        time.sleep(POLL_INTERVAL)

    raise TimeoutError(f"轮询超时（{MAX_POLL * POLL_INTERVAL} 秒）")


def main() -> int:
    parser = argparse.ArgumentParser(description="Agnes 视频生成")
    parser.add_argument("--prompt", help="视频提示词（动作/镜头描述）")
    parser.add_argument("--image", help="参考图本地路径（图生视频）")
    parser.add_argument("--image-url", help="参考图 URL（图生视频）")
    parser.add_argument("--out", help="输出视频路径")
    parser.add_argument("--size", default="720x1280", help="分辨率")
    parser.add_argument("--duration", type=int, default=5, help="时长（秒）")
    parser.add_argument("--check", action="store_true", help="仅检查配置与密钥")
    args = parser.parse_args()

    config = AgnesConfig.load()
    print(f"[配置] 站点={config.site}  base_url={config.base_url}")
    print(f"[配置] 视频模型={config.video_model}")

    if not has_api_key():
        print("[错误] 未检测到 AGNES_API_KEY 环境变量。", file=sys.stderr)
        return 2
    print("[密钥] AGNES_API_KEY 已就绪")

    if args.check:
        return 0
    if not args.prompt or not args.out:
        print("[错误] 需提供 --prompt 和 --out", file=sys.stderr)
        return 2

    # 图生视频：本地图片需先上传（此处仅支持已有 URL，本地上传待补充）
    image_url = args.image_url
    if args.image and not image_url:
        print("[警告] 暂未实现本地图片上传，请改用 --image-url", file=sys.stderr)
        return 2

    print("[调用] 创建视频任务...")
    try:
        task_id = create_video_task(
            config, args.prompt, args.size, args.duration, image_url
        )
        print(f"[任务] task_id={task_id}")
        print("[轮询] 等待生成完成...")
        video_url = poll_video_task(config, task_id)
        print(f"[完成] 视频 URL 已获取")
    except (AgnesAPIError, RuntimeError, TimeoutError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    dest = download_file(video_url, Path(args.out))
    print(f"[完成] 已保存到 {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

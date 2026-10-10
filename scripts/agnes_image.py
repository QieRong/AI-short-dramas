"""Agnes 图像模型适配脚本。

职责单一：调用 agnes-image-2.5-flash 生成图片，下载保存到本地。

用法：
    python agnes_image.py --prompt "角色设定图" --out ../04_assets/characters/hero.png
    python agnes_image.py --check
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agnes_client import (
    AgnesConfig,
    AgnesAPIError,
    download_file,
    has_api_key,
    request_json,
)


def generate_image(config: AgnesConfig, prompt: str, size: str = "1024x1024") -> str:
    """调用图像模型，返回图片 URL（或 b64 数据）。

    优先尝试 OpenAI 兼容的 /images/generations 端点。
    """
    result = request_json(
        config,
        "POST",
        "/images/generations",
        payload={
            "model": config.image_model,
            "prompt": prompt,
            "size": size,
            "n": 1,
        },
        timeout=180,
    )

    # 兼容两种返回形式
    try:
        item = result["data"][0]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"响应格式异常: {result}") from e

    if "url" in item:
        return item["url"]
    if "b64_json" in item:
        return f"b64:{item['b64_json']}"
    raise RuntimeError(f"未识别的响应字段: {item}")


def save_image(source: str, dest: Path) -> Path:
    """保存图片：URL 则下载，b64 则解码。"""
    if source.startswith("b64:"):
        import base64

        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(source[4:]))
        return dest
    return download_file(source, dest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Agnes 图像生成")
    parser.add_argument("--prompt", help="图像提示词")
    parser.add_argument("--out", help="输出图片路径")
    parser.add_argument("--size", default="1024x1024", help="图片尺寸")
    parser.add_argument("--check", action="store_true", help="仅检查配置与密钥")
    args = parser.parse_args()

    config = AgnesConfig.load()
    print(f"[配置] 站点={config.site}  base_url={config.base_url}")
    print(f"[配置] 图像模型={config.image_model}")

    if not has_api_key():
        print("[错误] 未检测到 AGNES_API_KEY 环境变量。", file=sys.stderr)
        return 2
    print("[密钥] AGNES_API_KEY 已就绪")

    if args.check:
        return 0
    if not args.prompt or not args.out:
        print("[错误] 需提供 --prompt 和 --out", file=sys.stderr)
        return 2

    print("[调用] 正在生成图片...")
    try:
        source = generate_image(config, args.prompt, args.size)
    except AgnesAPIError as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    dest = save_image(source, Path(args.out))
    print(f"[完成] 已保存到 {dest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

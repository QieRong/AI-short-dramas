"""Agnes 图像模型适配脚本。

职责单一：调用 agnes-image-2.5-flash 生成图片，下载保存到本地。

用法：
    python agnes_image.py --prompt "角色设定图" --out ../04_assets/characters/hero.png
    python agnes_image.py --prompt "分镜图" --out out.png --size 2K --ratio 9:16 \
        --ref ../04_assets/characters/林浅_护照.png
    python agnes_image.py --check

说明（依据官方 agnes-image-2.5-flash 文档）：
    - 尺寸推荐用档位式 size（"1K"/"2K"/"3K"/"4K"）配合 ratio（"9:16" 等）；
    - `response_format` 必须放在 `extra_body` 内，不得置于请求体顶层；
    - 图生图把参考图放进 `extra_body.image`（公网 URL 或 Data URI Base64），
      本地文件会自动转成 Data URI；**不需要**传 `tags:["img2img"]`。
"""

from __future__ import annotations

import argparse
import base64
import sys
from pathlib import Path
from typing import Any

from agnes_client import (
    AgnesConfig,
    AgnesAPIError,
    download_file,
    has_api_key,
    request_json,
)

# 本地图片后缀 → MIME 子类型
MIME_BY_SUFFIX = {"png": "png", "jpg": "jpeg", "jpeg": "jpeg", "webp": "webp"}


def to_data_uri(path: Path) -> str:
    """把本地图片编码为 Data URI Base64（官方支持的参考图输入形式）。"""
    mime = MIME_BY_SUFFIX.get(path.suffix.lower().lstrip("."), "png")
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/{mime};base64,{encoded}"


def resolve_ref(ref: str) -> str:
    """参考图解析：http(s) URL 原样返回；本地路径转为 Data URI。"""
    if ref.startswith(("http://", "https://")):
        return ref
    path = Path(ref)
    if not path.exists():
        raise FileNotFoundError(f"参考图不存在: {path}")
    return to_data_uri(path)


def generate_image(
    config: AgnesConfig,
    prompt: str,
    size: str = "1024x1024",
    ratio: str | None = None,
    refs: list[str] | None = None,
) -> str:
    """调用图像模型，返回图片 URL（或 b64 数据）。"""
    extra_body: dict[str, Any] = {"response_format": "url"}
    if refs:
        extra_body["image"] = [resolve_ref(r) for r in refs]

    payload: dict[str, Any] = {
        "model": config.image_model,
        "prompt": prompt,
        "size": size,
        "n": 1,
        "extra_body": extra_body,
    }
    if ratio:
        payload["ratio"] = ratio

    result = request_json(
        config,
        "POST",
        "/images/generations",
        payload=payload,
        timeout=300,
    )

    # 兼容两种返回形式
    try:
        item = result["data"][0]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"响应格式异常: {result}") from e

    if item.get("url"):
        return item["url"]
    if item.get("b64_json"):
        return f"b64:{item['b64_json']}"
    raise RuntimeError(f"未识别的响应字段: {item}")


def save_image(source: str, dest: Path) -> Path:
    """保存图片：URL 则下载，b64 则解码。"""
    if source.startswith("b64:"):
        dest.parent.mkdir(parents=True, exist_ok=True)
        dest.write_bytes(base64.b64decode(source[4:]))
        return dest
    return download_file(source, dest)


def main() -> int:
    parser = argparse.ArgumentParser(description="Agnes 图像生成")
    parser.add_argument("--prompt", help="图像提示词")
    parser.add_argument("--out", help="输出图片路径")
    parser.add_argument("--size", default="1024x1024",
                        help='尺寸：档位式 "1K"/"2K"/"3K"/"4K" 或精确值 "1024x1024"')
    parser.add_argument("--ratio", default=None,
                        help='宽高比：与档位式 size 配合，如 "9:16"')
    parser.add_argument("--ref", action="append", default=None,
                        help="参考图（图生图/多图合成），可重复；本地路径或 http(s) URL")
    parser.add_argument("--check", action="store_true", help="仅检查配置与密钥")
    args = parser.parse_args()

    config = AgnesConfig.load()
    print(f"[配置] 站点={config.site}  base_url={config.base_url}")
    print(f"[配置] 图像模型={config.image_model}")
    print(f"[配置] size={args.size}" + (f"  ratio={args.ratio}" if args.ratio else ""))

    if not has_api_key():
        print("[错误] 未检测到 AGNES_API_KEY 环境变量。", file=sys.stderr)
        return 2
    print("[密钥] AGNES_API_KEY 已就绪")

    if args.check:
        return 0
    if not args.prompt or not args.out:
        print("[错误] 需提供 --prompt 和 --out", file=sys.stderr)
        return 2

    if args.ref:
        print(f"[参考图] 共 {len(args.ref)} 张：" + "，".join(Path(r).name for r in args.ref))

    print("[调用] 正在生成图片（可能需要数秒到数十秒）...")
    try:
        source = generate_image(config, args.prompt, args.size, args.ratio, args.ref)
    except (AgnesAPIError, FileNotFoundError) as e:
        print(f"[错误] {e}", file=sys.stderr)
        return 1

    dest = save_image(source, Path(args.out))
    size_kb = dest.stat().st_size / 1024
    print(f"[完成] 已保存到 {dest}（{size_kb:.0f} KB）")
    return 0


if __name__ == "__main__":
    sys.exit(main())

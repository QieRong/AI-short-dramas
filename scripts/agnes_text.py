"""Agnes 文本模型适配脚本。

职责单一：调用 agnes-3.0-flash 生成文本，保存到指定文件。

用法：
    python agnes_text.py --prompt "写一段剧本" --out ../02_scripts/EP01.md
    python agnes_text.py --prompt-file prompt.txt --out out.md
    python agnes_text.py --check          # 仅检查配置与密钥
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from agnes_client import (
    AgnesConfig,
    MissingAPIKeyError,
    has_api_key,
    request_json,
)


def generate_text(config: AgnesConfig, prompt: str, system: str | None = None) -> str:
    """调用文本模型，返回生成的文本内容。"""
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    result = request_json(
        config,
        "POST",
        "/chat/completions",
        payload={
            "model": config.text_model,
            "messages": messages,
            "temperature": 0.8,
            "max_tokens": 4096,
        },
    )

    try:
        return result["choices"][0]["message"]["content"]
    except (KeyError, IndexError) as e:
        raise RuntimeError(f"响应格式异常: {result}") from e


def main() -> int:
    parser = argparse.ArgumentParser(description="Agnes 文本生成")
    parser.add_argument("--prompt", help="提示词")
    parser.add_argument("--prompt-file", help="从文件读取提示词")
    parser.add_argument("--out", help="输出文件路径")
    parser.add_argument("--system", help="系统提示词")
    parser.add_argument("--check", action="store_true", help="仅检查配置与密钥")
    args = parser.parse_args()

    config = AgnesConfig.load()
    print(f"[配置] 站点={config.site}  base_url={config.base_url}")
    print(f"[配置] 文本模型={config.text_model}")

    if not has_api_key():
        print("[错误] 未检测到 AGNES_API_KEY 环境变量。", file=sys.stderr)
        return 2
    print("[密钥] AGNES_API_KEY 已就绪")

    if args.check:
        return 0

    prompt = args.prompt
    if args.prompt_file:
        prompt = Path(args.prompt_file).read_text(encoding="utf-8")
    if not prompt:
        print("[错误] 需提供 --prompt 或 --prompt-file", file=sys.stderr)
        return 2

    print("[调用] 正在生成文本...")
    text = generate_text(config, prompt, args.system)

    if args.out:
        out_path = Path(args.out)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(text, encoding="utf-8")
        print(f"[完成] 已保存到 {out_path}（{len(text)} 字）")
    else:
        print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())

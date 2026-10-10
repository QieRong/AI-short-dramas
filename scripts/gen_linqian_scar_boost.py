"""林浅护照 · 疤痕加强（第二轮 img2img）。

输入：第一轮已补疤版本 `林浅_护照_补疤img2img_1_半身露腕.png`
      （面孔已保住、疤已出现，但疤偏淡、构图偏侧身）

目标（用户指定）：
    1. 加深左腕内侧疤痕 → 成为清晰可辨的视觉元素（手机屏也看得清）
    2. 保持半身构图，但让脸部更突出（避免过度侧身）

产出 2 张候选，供用户择一。

用法：
    python gen_linqian_scar_boost.py
"""

from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

from agnes_client import AgnesConfig, AgnesAPIError, download_file, request_json

OUT_DIR = Path(__file__).resolve().parent.parent / "04_assets" / "characters"
SRC = OUT_DIR / "林浅_护照_补疤img2img_1_半身露腕.png"

PROMPTS = [
    (
        "在不改变人物面部五官、发型、年龄与气质的前提下："
        "1) 显著加深并强化左手腕内侧的疤痕——使其呈清晰的淡红棕色愈合疤痕，"
        "边缘分明、略带凸起、质感真实，即使缩小到手机屏幕也清晰可辨，"
        "疤痕长度约5厘米，居中于腕部内侧；"
        "2) 将构图调整为更居中的半身肖像，面部朝向镜头、正对观者，占比更大更突出，"
        "左手自然抬至胸前露出手腕；"
        "保留：原始面孔、黑白极简风衣、写实胶片摄影质感、柔和自然光。9:16 竖屏。",
        "A_居中半身",
    ),
    (
        "保持输入图像中人物的面容、眼神与身份完全一致："
        "1) 让左手腕内侧的疤痕更醒目——颜色略深（淡红棕）、纹理清晰、"
        "可见愈合后的轻微增生，成为一个明确的视觉焦点，远景亦能辨认；"
        "2) 人物正脸/微侧朝向镜头，半身构图，面部位于画面上部三分之一并清晰突出，"
        "左腕自然呈现于胸前下方。"
        "保留写实电影感摄影与冷色调。9:16 竖屏。",
        "B_正脸突出",
    ),
]


def _data_uri(p: Path) -> str:
    return "data:image/png;base64," + base64.b64encode(p.read_bytes()).decode("ascii")


def main() -> int:
    if not SRC.exists():
        print(f"[错误] 找不到输入图 {SRC}", file=sys.stderr)
        return 2
    config = AgnesConfig.load()
    uri = _data_uri(SRC)
    print(f"[输入] {SRC.name}")

    results = []
    for i, (prompt, tag) in enumerate(PROMPTS, 1):
        fname = f"林浅_护照_疤加强_{i}_{tag}.png"
        out = OUT_DIR / fname
        print(f"\n[{i}/{len(PROMPTS)}] {tag} -> {fname}")
        try:
            r = request_json(
                config, "POST", "/images/generations",
                payload={
                    "model": config.image_model,
                    "prompt": prompt,
                    "size": "1K",
                    "ratio": "9:16",
                    "extra_body": {"image": [uri], "response_format": "url"},
                },
                timeout=240,
            )
            item = r["data"][0]
            src = item.get("url") or f"b64:{item.get('b64_json','')}"
            if src.startswith("b64:"):
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(base64.b64decode(src[4:]))
            else:
                download_file(src, out)
            print(f"    ✅ {out.name}")
            results.append({"file": fname, "tag": tag, "ok": True})
        except AgnesAPIError as e:
            print(f"    ❌ {str(e)[:200]}")
            results.append({"file": fname, "tag": tag, "ok": False, "error": str(e)[:300]})
        time.sleep(3)

    (OUT_DIR / "_manifest_scar_boost.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[清单] {OUT_DIR / '_manifest_scar_boost.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

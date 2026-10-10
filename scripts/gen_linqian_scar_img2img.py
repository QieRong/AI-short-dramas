"""林浅护照补疤 —— 使用图生图（img2img）在选定护照图上添加左手腕旧疤。

依据官方文档（agnes-image-2.5-flash）：
    POST /v1/images/generations
    extra_body.image = [ "data:image/png;base64,...." ]   # 输入参考图
    extra_body.response_format = "url"

思路：以用户选定的 林浅_3_疲惫.png 为输入，指令模型**保留面孔与风格**，
      仅调整构图/姿势使左手腕内侧露出，并加上一道陈旧疤痕。

用法：
    python gen_linqian_scar_img2img.py
"""

from __future__ import annotations

import base64
import json
import sys
import time
from pathlib import Path

from agnes_client import AgnesConfig, AgnesAPIError, download_file, request_json

OUT_DIR = Path(__file__).resolve().parent.parent / "04_assets" / "characters"
SRC = OUT_DIR / "林浅_3_疲惫.png"   # 用户选定的护照基准

# 图生图提示词结构：[改变要求]+[新场景/风格]+[添加/移除元素]+[保留元素]
PROMPTS = [
    (
        "在不改变人物面部五官、发型、年龄与整体气质的前提下，"
        "将构图调整为半身像：人物左臂自然抬起横于胸前，左前臂内侧朝镜头，"
        "风衣袖口挽起露出手腕；在左手腕内侧清楚添加一道陈旧疤痕"
        "（长约5厘米、淡白色、微微凸起、愈合多年）。"
        "保留：原始面孔特征、黑白极简风衣、写实胶片摄影风格、柔和自然光。"
        "9:16 竖屏。",
        "半身露腕",
    ),
    (
        "保持输入图像的人物身份、面容、发型完全一致，改为侧身半身构图，"
        "双臂环抱，左手腕从挽起的袖口完整露出并朝向镜头，"
        "腕内侧添加一道清晰可辨的陈旧疤痕（细长、浅色、愈合已久）。"
        "保留写实电影感摄影质感与冷色调光影。9:16 竖屏。",
        "侧身环抱",
    ),
]


def _data_uri(path: Path) -> str:
    b64 = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{b64}"


def main() -> int:
    if not SRC.exists():
        print(f"[错误] 找不到源图 {SRC}", file=sys.stderr)
        return 2
    config = AgnesConfig.load()
    uri = _data_uri(SRC)
    print(f"[输入] {SRC.name}  (base64 {len(uri)} 字符)")

    results = []
    for i, (prompt, tag) in enumerate(PROMPTS, 1):
        fname = f"林浅_护照_补疤img2img_{i}_{tag}.png"
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
                    "extra_body": {
                        "image": [uri],
                        "response_format": "url",
                    },
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

    (OUT_DIR / "_manifest_scar_img2img.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[清单] {OUT_DIR / '_manifest_scar_img2img.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

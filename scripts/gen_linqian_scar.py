"""林浅角色护照补图 —— 明确展示左手腕旧疤。

背景：用户选定 林浅_3_疲惫.png 作为护照基准，但该图为近景特写，
      左手腕旧疤未出现。旧疤是后续剧情关键伏笔，必须补。

策略：以"疲惫·特写"的同一面孔与风格为基准，重新生成 3 张含
      **清晰的左手腕旧疤** 构图（半身/手部特写），供用户择一作为最终护照图。

用法：
    python gen_linqian_scar.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

from agnes_client import AgnesConfig, AgnesAPIError, download_file, request_json

OUT_DIR = Path(__file__).resolve().parent.parent / "04_assets" / "characters"

# 与选定护照图一致的面孔/风格基准
BASE = (
    "中国女性，24-26岁，冷艳疏离，眼底带疲惫感；"
    "鹅蛋脸、剑眉、薄唇，黑中长发低马尾；"
    "穿黑白极简风衣"
)
STYLE = (
    "电影感写实摄影，35mm 胶片质感，浅景深，柔和自然光，"
    "纯色或虚化背景，高细节皮肤质感，非动漫，非3D渲染，不要过度美颜，真实可信的亚洲面孔"
)

SHOTS = [
    (
        "半身正面像，人物将左臂抬起横于胸前，左前臂内侧（腕上方）完全朝向镜头，"
        "**画面焦点明确落在左手腕上一道正在愈合的陈旧疤痕**：长约 5 厘米、"
        "略白于肤色、微微凸起、愈合多年，清晰可辨；"
        "风衣袖口挽至肘部，确保手腕与疤痕不被遮挡；表情疲惫隐忍，目光低垂",
        "正面抬臂 · 疤清晰",
    ),
    (
        "极近特写，仅拍摄左侧前臂与手腕，占满画面，"
        "**左手腕内侧一道细长的陈旧疤痕居中、高清、锐利对焦**，"
        "疤痕呈淡白色、轻微增生、愈合多年，周围皮肤可见自然纹理与微小毛孔；"
        "柔和侧光勾勒疤痕轮廓，背景虚化",
        "腕部极特写 · 疤高清",
    ),
    (
        "半身，人物双臂环抱，左臂在外，左手腕从挽起的袖口完整露出并朝向镜头，"
        "**腕内侧一道清晰可见的陈旧疤痕**，眼神疏离冷峻，强烈明暗对比",
        "环抱 · 腕露疤",
    ),
]


def main() -> int:
    config = AgnesConfig.load()
    results = []
    for i, (desc, tag) in enumerate(SHOTS, 1):
        prompt = f"{BASE}。{desc}。{STYLE}。9:16 竖屏构图。"
        fname = f"林浅_护照候选_补疤v2_{i}_{tag.split(' · ')[-1]}.png"
        out = OUT_DIR / fname
        print(f"[{i}/{len(SHOTS)}] {tag} -> {fname}")
        try:
            r = request_json(
                config, "POST", "/images/generations",
                payload={"model": config.image_model, "prompt": prompt,
                         "size": "720x1280", "n": 1},
                timeout=180,
            )
            item = r["data"][0]
            src = item.get("url") or f"b64:{item.get('b64_json','')}"
            if src.startswith("b64:"):
                import base64
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(base64.b64decode(src[4:]))
            else:
                download_file(src, out)
            print(f"    ✅ {out.name}")
            results.append({"file": fname, "tag": tag, "ok": True, "prompt": prompt})
        except AgnesAPIError as e:
            print(f"    ❌ {str(e)[:160]}")
            results.append({"file": fname, "tag": tag, "ok": False, "error": str(e)[:200]})
        time.sleep(3)

    (OUT_DIR / "_manifest_scar.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[清单] {OUT_DIR / '_manifest_scar.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

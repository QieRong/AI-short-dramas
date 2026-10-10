"""角色候选图批量生成 —— 林浅 5 张 + 顾承泽 5 张。

依据用户指定的角色形象偏好（见 04_assets/characters/角色形象说明.md）。
统一要求：
    - 9:16 竖屏
    - 电影感写实（非 anime / 非 3D 渲染 / 不过度美颜）
    - 纯色或虚化背景
    - 每张配一句形象说明

用法：
    python gen_characters.py              # 生成全部 10 张
    python gen_characters.py --who 林浅    # 只生成林浅
    python gen_characters.py --dry-run    # 只打印提示词，不调用
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from agnes_client import AgnesConfig, AgnesAPIError, download_file, has_api_key, request_json

OUT_DIR = Path(__file__).resolve().parent.parent / "04_assets" / "characters"

# 统一风格后缀（电影感写实）
STYLE = (
    "电影感写实摄影，9:16 竖屏构图，35mm 胶片质感，浅景深，"
    "柔和自然光，纯色或虚化背景，高细节皮肤质感，非动漫，非3D渲染，"
    "不要过度美颜，真实可信的亚洲面孔"
)

# 角色定义：每人 5 个变体（角度/表情/造型微调），保证一致性同时提供选择空间
CHARACTERS = {
    "林浅": {
        "base": (
            "中国女性，24-26岁，冷艳疏离，眼底带疲惫感；"
            "鹅蛋脸、剑眉、薄唇，黑中长发低马尾；"
            "穿黑白极简风衣，左手腕有一道旧疤"
        ),
        "vibe": "像收在鞘里的刀",
        "shots": [
            ("正面半身，平静直视镜头，表情克制", "正脸 · 克制"),
            ("四分之三侧脸，微微侧光，眼神凌厉", "侧光 · 凌厉"),
            ("近景特写，目光低垂，透出疲惫与隐忍", "特写 · 疲惫"),
            ("全身，双手插兜，站立姿态疏离", "全身 · 疏离"),
            ("仰角半身，风吹起碎发，下颌线分明", "仰角 · 冷峻"),
        ],
    },
    "顾承泽": {
        "base": (
            "中国男性，28-32岁，玩世不恭带痞气；"
            "轮廓分明、眉骨高，深棕短发微乱；"
            "穿深色三件套西装，戴金丝细框眼镜，"
            "左手腕一只旧机械表（表带带划痕）"
        ),
        "vibe": "笑着说话，但随时可能拔刀",
        "shots": [
            ("正面半身，似笑非笑，眼神审视", "正脸 · 审视"),
            ("四分之三侧脸，单手扶眼镜，嘴角微勾", "侧脸 · 扶镜"),
            ("近景特写，眼神锐利穿透，笑意收敛", "特写 · 锐利"),
            ("全身，单手插兜，西装笔挺站姿松弛", "全身 · 松弛"),
            ("侧逆光半身，镜片反光遮住眼神，气场冷冽", "逆光 · 冷冽"),
        ],
    },
}


def build_prompt(name: str, shot_desc: str) -> str:
    c = CHARACTERS[name]
    return f"{c['base']}。{shot_desc}。整体气质：{c['vibe']}。{STYLE}。"


def gen_one(config: AgnesConfig, prompt: str, out: Path) -> bool:
    try:
        result = request_json(
            config, "POST", "/images/generations",
            payload={"model": config.image_model, "prompt": prompt,
                     "size": "720x1280", "n": 1},
            timeout=180,
        )
    except AgnesAPIError as e:
        print(f"    ❌ 失败: {str(e)[:160]}")
        return False
    item = result["data"][0]
    src = item.get("url") or f"b64:{item.get('b64_json','')}"
    if src.startswith("b64:"):
        import base64
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_bytes(base64.b64decode(src[4:]))
    else:
        download_file(src, out)
    print(f"    ✅ 已保存 {out.name}")
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--who", choices=list(CHARACTERS), help="只生成某角色")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    config = AgnesConfig.load()
    names = [args.who] if args.who else list(CHARACTERS)

    manifest = {}
    for name in names:
        print(f"\n=== {name} ===")
        manifest[name] = []
        for i, (desc, tag) in enumerate(CHARACTERS[name]["shots"], 1):
            prompt = build_prompt(name, desc)
            fname = f"{name}_{i}_{tag.split(' · ')[1]}.png"
            out = OUT_DIR / fname
            print(f"  [{i}/5] {tag}")
            if args.dry_run:
                print(f"    prompt: {prompt}")
                manifest[name].append({"file": fname, "tag": tag, "desc": desc,
                                        "prompt": prompt})
                continue
            ok = gen_one(config, prompt, out)
            manifest[name].append({"file": fname, "tag": tag, "desc": desc,
                                    "ok": ok, "prompt": prompt})
            time.sleep(3)  # 轻微间隔，降低限流风险

    if not args.dry_run:
        (OUT_DIR / "_manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"\n[清单] 已写入 {OUT_DIR / '_manifest.json'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

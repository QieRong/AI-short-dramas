"""视频配额测试 v2 —— 使用官方正确 schema。

schema（官方文档）：
    mode="text", seconds="4"（最短）, size="720P", aspect_ratio="9:16"

目标（用户指定）：
    记录：调用时间、连续调用第几次触发 429、冷却时长。

策略：
    - 单次创建任务，观察是否 429。
    - 若成功 → 记录基线后停止（不下载，省带宽）。
    - 若 429 → 冷却探测（60s 间隔，最多 5 次），记录恢复时长。
    - 任何"付费提示"立即停止。
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from agnes_client import AgnesConfig, AgnesAPIError, request_json

LOG = Path(__file__).resolve().parent.parent / "04_assets" / "video" / "_quota_v2.json"
PROMPT = "深夜地下档案室，一只手缓缓攥紧黑色U盘，冷色调，电影感特写，镜头轻微推进"


def try_create(config) -> tuple[bool, str, str]:
    payload = {
        "model": config.video_model,
        "prompt": PROMPT,
        "mode": "text",
        "seconds": "4",
        "size": "720P",
        "aspect_ratio": "9:16",
        "n": 1,
    }
    try:
        r = request_json(config, "POST", "/videos", payload=payload, timeout=90)
        vid = r.get("video_id") or r.get("id") or "?"
        return True, f"video_id={vid}", json.dumps(r, ensure_ascii=False)[:300]
    except AgnesAPIError as e:
        s = str(e)
        if "rate_limit" in s:
            code = "429"
        elif "upgrade" in s.lower() or "token plan" in s.lower():
            code = "PAID"
        elif "invalid" in s.lower():
            code = "INVALID"
        else:
            code = "ERR"
        return False, code, s[:300]


def main() -> int:
    config = AgnesConfig.load()
    print("=" * 60)
    print("视频配额测试 v2（官方 schema：mode=text, seconds=4, size=720P）")
    print("=" * 60)

    events = []
    ts = lambda: datetime.now().strftime("%H:%M:%S")  # noqa: E731

    ok, msg, detail = try_create(config)
    events.append({"time": ts(), "success": ok, "msg": msg, "detail": detail[:200]})
    print(f"[{ts()}] 首次调用: {'✅ ' + msg if ok else '❌ ' + msg}")

    if ok:
        print("\n✅ 首次调用成功！免费层可用。")
        print("   说明：为省额度，未做连续调用压力测试。")
        _write(events, recovered=None, note="first_call_success")
        return 0

    if msg == "PAID":
        print(f"\n⛔ 付费提示！立即停止。详情：{detail}")
        _write(events, recovered=None, note="paid_prompt")
        return 1

    if msg == "INVALID":
        print(f"\n❌ schema 仍不合法：{detail}")
        _write(events, recovered=None, note="invalid_schema")
        return 2

    # 429 → 冷却探测
    print(f"\n⛔ 首次即 429。开始冷却探测（60s 间隔，最多 5 次）...\n")
    for i in range(1, 6):
        time.sleep(60)
        waited = i * 60
        ok, msg, detail = try_create(config)
        events.append({"time": ts(), "success": ok, "msg": msg,
                       "waited_s": waited, "detail": detail[:200]})
        print(f"[{ts()}] 冷却 {waited}s 后: {'✅ 成功' if ok else '❌ ' + msg}")
        if ok:
            _write(events, recovered=waited, note="recovered")
            print(f"\n✅ 冷却 {waited}s 后恢复。")
            return 0

    _write(events, recovered=None, note="not_recovered_5min")
    print("\n⚠️ 5 分钟仍未恢复。")
    return 1


def _write(events, recovered, note):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps({
        "probe_time": datetime.now().isoformat(),
        "recovered_after_s": recovered,
        "note": note,
        "events": events,
    }, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n[日志] {LOG}")


if __name__ == "__main__":
    sys.exit(main())

"""冷却探测 —— 用已知合法 schema 测 429 恢复时长。

已知：
    合法最小 schema = model + mode + prompt（duration 非法）
    连续调用时，第 2 次即触发 429（第 1 次合法调用可能已消耗窗口）

目标（用户指定）：记录冷却时长 —— 多久后能再次成功创建任务。

策略：
    每 30 秒尝试一次 `model+mode+prompt`，记录每次结果与累计等待，
    直到成功或达到上限（10 次 / 5 分钟）。
    一旦成功即停止（不继续烧额度）。
"""

from __future__ import annotations

import json
import sys
import time
from datetime import datetime
from pathlib import Path

from agnes_client import AgnesConfig, AgnesAPIError, request_json

LOG = Path(__file__).resolve().parent.parent / "04_assets" / "video" / "_cooldown_log.json"
PROMPT = "深夜档案室，一只手攥紧U盘，冷光特写"
INTERVAL = 30
MAX_TRIES = 10


def try_once(config) -> tuple[bool, str, str]:
    """返回 (成功?, 错误码, 详情)。"""
    payload = {"model": config.video_model, "mode": "t2v", "prompt": PROMPT}
    try:
        r = request_json(config, "POST", "/videos", payload=payload, timeout=60)
        return True, "", json.dumps(r, ensure_ascii=False)[:300]
    except AgnesAPIError as e:
        s = str(e)
        code = "rate_limit" if "rate_limit" in s else ("paid" if "upgrade" in s.lower() and "429" not in s else "other")
        return False, code, s[:300]


def main() -> int:
    config = AgnesConfig.load()
    print("=" * 60)
    print("视频 429 冷却探测")
    print("=" * 60)
    print(f"schema: model+mode(t2v)+prompt | 间隔 {INTERVAL}s | 上限 {MAX_TRIES} 次\n")

    events = []
    start = time.time()

    for i in range(1, MAX_TRIES + 1):
        waited = round(time.time() - start, 1)
        ok, code, detail = try_once(config)
        ts = datetime.now().strftime("%H:%M:%S")
        events.append({"try": i, "time": ts, "waited_s": waited,
                       "success": ok, "code": code, "detail": detail[:200]})
        print(f"[{ts}] 第 {i} 次（已等 {waited}s）: "
              f"{'✅ 成功' if ok else '❌ ' + code}")

        if ok:
            LOG.parent.mkdir(parents=True, exist_ok=True)
            LOG.write_text(json.dumps({"probe_time": datetime.now().isoformat(),
                                       "recovered_after_s": waited, "events": events},
                                      ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"\n✅ 冷却 {waited}s 后恢复。日志：{LOG}")
            return 0

        if code == "paid":
            print("\n⛔ 疑似付费提示，立即停止。详情：", detail)
            break

        if i < MAX_TRIES:
            time.sleep(INTERVAL)

    LOG.parent.mkdir(parents=True, exist_ok=True)
    LOG.write_text(json.dumps({"probe_time": datetime.now().isoformat(),
                               "recovered_after_s": None, "events": events},
                              ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n⚠️ {MAX_TRIES} 次（共 {round(time.time()-start,1)}s）仍未恢复。日志：{LOG}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

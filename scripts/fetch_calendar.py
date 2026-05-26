"""
fetch_calendar.py — schedule.yml에서 캘린더 이벤트를 읽어 윈도우(T-7 ~ T+28)로 필터링.

v1 단계에서는 외부 API 호출 없이 정적 YAML을 사용한다.
v2에서 Bloomberg ECO 함수 / investing.com 등으로 실시간 보강 예정.

결과: data/calendar/latest.json

Usage:
    python scripts/fetch_calendar.py
"""
from __future__ import annotations

import json
import sys
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import yaml

import config

ROOT = Path(__file__).resolve().parent.parent
SCHEDULE_PATH = ROOT / "data" / "calendar" / "schedule.yml"
OUT_PATH = ROOT / "data" / "calendar" / "latest.json"

WINDOW_BACK_DAYS = 7
WINDOW_FORWARD_DAYS = 28


def main() -> None:
    if not SCHEDULE_PATH.exists():
        print(f"ERROR: {SCHEDULE_PATH} not found", file=sys.stderr)
        sys.exit(1)

    schedule = yaml.safe_load(SCHEDULE_PATH.read_text(encoding="utf-8"))
    raw_events = schedule.get("events", [])

    today = date.today()
    start = today - timedelta(days=WINDOW_BACK_DAYS)
    end = today + timedelta(days=WINDOW_FORWARD_DAYS)

    in_window: list[dict] = []
    dropped_unknown = 0
    dropped_outside = 0

    for ev in raw_events:
        try:
            ev_date = date.fromisoformat(ev["date"])
        except (KeyError, ValueError):
            print(f"  skip (bad date): {ev}", file=sys.stderr)
            continue

        if not (start <= ev_date <= end):
            dropped_outside += 1
            continue

        ind = config.get_indicator(ev["indicator_id"])
        if not ind:
            print(f"  skip (unknown indicator): {ev['indicator_id']}", file=sys.stderr)
            dropped_unknown += 1
            continue

        in_window.append({
            "date": ev["date"],
            "country": ind["country"],
            "indicator_id": ev["indicator_id"],
            "time_kst": ev.get("time_kst", ""),
            "note": ev.get("note", ""),
        })

    # sort by date then time
    in_window.sort(key=lambda e: (e["date"], e["time_kst"]))

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "window_start": start.isoformat(),
        "window_end": end.isoformat(),
        "source": "schedule.yml",
        "events": in_window,
    }
    OUT_PATH.write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"[calendar] Window: {start} ~ {end}")
    print(f"[calendar] {len(in_window)} events in window "
          f"({dropped_outside} outside, {dropped_unknown} unknown indicator)")
    print(f"[calendar] Saved to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

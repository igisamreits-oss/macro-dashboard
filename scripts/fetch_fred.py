"""
fetch_fred.py — US 지표 FRED API에서 fetch.

FRED는 인덱스 레벨(예: CPIAUCSL=320.32)만 주므로 12개월 YoY를 직접 계산한다.
정책금리(FOMC)는 최신값만 가져온다.

결과: data/fred/latest.json

Usage:
    $env:FRED_API_KEY = "xxx"
    python scripts/fetch_fred.py
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

import config

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "fred" / "latest.json"

FRED_BASE = "https://api.stlouisfed.org/fred"


def get_observations(series_id: str, api_key: str, limit: int = 24) -> list[dict]:
    r = requests.get(
        f"{FRED_BASE}/series/observations",
        params={
            "series_id": series_id,
            "api_key": api_key,
            "file_type": "json",
            "sort_order": "desc",
            "limit": limit,
        },
        timeout=15,
    )
    r.raise_for_status()
    return r.json().get("observations", [])


def compute_yoy(obs: list[dict]) -> tuple[float | None, float | None, str | None]:
    """월간 인덱스 시리즈에서 최신·직전월 YoY를 계산.

    Returns: (latest_yoy, prior_yoy, latest_obs_date)
    """
    valid = {o["date"]: float(o["value"]) for o in obs if o["value"] not in (".", "")}
    if not valid:
        return None, None, None

    dates_desc = sorted(valid.keys(), reverse=True)
    latest_date = dates_desc[0]
    latest_v = valid[latest_date]

    def _yoy_for(d: str) -> float | None:
        y, m = int(d[:4]), int(d[5:7])
        base = f"{y - 1:04d}-{m:02d}-01"
        bv = valid.get(base)
        if bv is None or bv == 0:
            return None
        return round(((valid[d] / bv) - 1) * 100, 1)

    latest_yoy = _yoy_for(latest_date)
    prior_yoy = _yoy_for(dates_desc[1]) if len(dates_desc) >= 2 else None
    return latest_yoy, prior_yoy, latest_date


def fetch_latest_rate(series_id: str, api_key: str) -> tuple[float | None, str | None]:
    obs = get_observations(series_id, api_key, limit=5)
    for o in obs:
        if o["value"] not in (".", ""):
            return round(float(o["value"]), 2), o["date"]
    return None, None


def main() -> None:
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        print("ERROR: FRED_API_KEY environment variable not set.", file=sys.stderr)
        print("  Get a free key at https://fredaccount.stlouisfed.org/apikeys", file=sys.stderr)
        sys.exit(1)

    indicators_out: dict[str, dict] = {}
    cb_out: dict[str, dict] = {}

    for ind in config.INDICATORS:
        sid = ind.get("fred")
        if not sid:
            continue
        try:
            print(f"[fred] {ind['id']:20s} ({sid}) ...", end=" ", flush=True)
            if ind["category"] == "inflation":
                latest, prior, ldate = compute_yoy(get_observations(sid, api_key))
                indicators_out[ind["id"]] = {
                    "actual": latest,
                    "prior": prior,
                    "consensus": None,  # FRED 미제공
                    "release_date": ldate,
                    "source": "fred",
                }
                print(f"YoY={latest}% (prior={prior}%) date={ldate}")
            elif ind["category"] == "central_bank":
                rate, rdate = fetch_latest_rate(sid, api_key)
                cb_out[ind["id"]] = {
                    "rate": rate,
                    "next_meeting": None,
                    "consensus_rate": None,
                    "as_of": rdate,
                    "source": "fred",
                }
                print(f"rate={rate}% (as of {rdate})")
        except Exception as e:
            print(f"FAIL: {e}")

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "indicators": indicators_out,
        "central_banks": cb_out,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    print(f"\n[fred] Saved to {OUT_PATH.relative_to(ROOT)}")
    print(f"[fred] {len(indicators_out)} indicators, {len(cb_out)} central banks")


if __name__ == "__main__":
    main()

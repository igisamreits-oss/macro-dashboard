"""
fetch_bloomberg.py — 블룸버그 PC 전용 데이터 수집기.

세 가지 종류의 데이터를 한번에 처리:
  1. 스냅샷 (Daily/Weekly): PX_LAST + 1D delta
  2. 이벤트 (Monthly/Quarterly): 최신 actual + prior + 관측일
  3. 중앙은행 정책금리: PX_LAST

이 스크립트는 블룸버그 터미널이 로그인된 PC에서만 작동한다.
GitHub Actions에서는 절대 실행되지 않는다.

결과: data/bloomberg/latest.json

Usage:
    python scripts/fetch_bloomberg.py
    python scripts/fetch_bloomberg.py --tickers CPI YOY Index,FDTR Index  # 특정 티커만
"""
from __future__ import annotations

import argparse
import json
import sys
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

import pandas as pd
from xbbg import blp

import config

ROOT = Path(__file__).resolve().parent.parent
OUT_PATH = ROOT / "data" / "bloomberg" / "latest.json"


# ── 데이터 추출 헬퍼 ──────────────────────────────────────────────────
def _to_pandas(df) -> pd.DataFrame:
    """xbbg가 narwhals를 반환할 수 있으므로 pandas로 정규화."""
    if hasattr(df, "to_pandas"):
        return df.to_pandas()
    if hasattr(df, "to_native"):
        native = df.to_native()
        if hasattr(native, "to_pandas"):
            return native.to_pandas()
        return native
    return df


def _extract_long(df: pd.DataFrame) -> pd.DataFrame:
    """xbbg 1.2.4+ long format(ticker/date/field/value)에서 date 정렬된 값 series 추출."""
    if df is None or df.empty:
        return pd.DataFrame()
    if "value" not in df.columns or "date" not in df.columns:
        return pd.DataFrame()
    sub = df[["date", "value"]].dropna(subset=["value"]).copy()
    sub["date"] = pd.to_datetime(sub["date"])
    sub = sub.sort_values("date")
    return sub


def fetch_snapshot(ticker: str) -> dict:
    """Daily/Weekly 스냅샷: 최신 PX_LAST + 1D delta."""
    end = date.today()
    start = end - timedelta(days=14)
    raw = blp.bdh(ticker, "PX_LAST", start_date=start, end_date=end)
    df = _extract_long(_to_pandas(raw))
    if df.empty:
        return {"value": None, "change_1d": None, "as_of": None, "error": "empty"}

    latest = float(df["value"].iloc[-1])
    change_1d = None
    if len(df) >= 2:
        change_1d = round(latest - float(df["value"].iloc[-2]), 4)
    return {
        "value": round(latest, 4),
        "change_1d": change_1d,
        "as_of": df["date"].iloc[-1].strftime("%Y-%m-%d"),
    }


def fetch_event(ticker: str) -> dict:
    """Monthly/Quarterly 이벤트: 최신 actual + prior + 관측일."""
    end = date.today()
    start = end - timedelta(days=540)
    raw = blp.bdh(ticker, "PX_LAST", start_date=start, end_date=end)
    df = _extract_long(_to_pandas(raw))
    if df.empty:
        return {"actual": None, "prior": None, "consensus": None, "release_date": None, "error": "empty"}

    actual = float(df["value"].iloc[-1])
    prior = float(df["value"].iloc[-2]) if len(df) >= 2 else None
    return {
        "actual": round(actual, 4),
        "prior": round(prior, 4) if prior is not None else None,
        "consensus": None,  # v2에서 ECO_SURVEY_MEDIAN 추가 예정
        "release_date": df["date"].iloc[-1].strftime("%Y-%m-%d"),
    }


def fetch_cb_rate(ticker: str) -> dict:
    """중앙은행 정책금리: PX_LAST."""
    raw = blp.bdp(ticker, "PX_LAST")
    df = _to_pandas(raw)
    if df is None or df.empty:
        return {"rate": None, "next_meeting": None, "consensus_rate": None, "error": "empty"}

    if "value" in df.columns:
        val = df["value"].iloc[0]
    elif "PX_LAST" in df.columns:
        val = df["PX_LAST"].iloc[0]
    else:
        val = df.iloc[0, 0]
    if pd.isna(val):
        return {"rate": None, "next_meeting": None, "consensus_rate": None, "error": "no data"}

    return {
        "rate": round(float(val), 4),
        "next_meeting": None,
        "consensus_rate": None,
    }


# ── Main ─────────────────────────────────────────────────────────────
def main(ticker_filter: list[str] | None = None) -> None:
    indicators_out: dict[str, dict] = {}
    snapshots_out: dict[str, dict] = {}
    cb_out: dict[str, dict] = {}

    total = 0
    success = 0
    failed = []

    for ind in config.INDICATORS:
        ticker = ind.get("bbg")
        if not ticker:
            continue
        if ticker_filter and ticker not in ticker_filter:
            continue
        total += 1

        cat = ind["category"]
        cat_meta = config.CATEGORIES[cat]

        try:
            print(f"  [{ind['id']:30s}] {ticker:24s} ...", end=" ", flush=True)
            if cat == "central_bank":
                result = fetch_cb_rate(ticker)
                if result.get("rate") is not None:
                    cb_out[ind["id"]] = result
                    print(f"rate={result['rate']}%")
                    success += 1
                else:
                    print(f"FAIL: {result.get('error', 'no rate')}")
                    failed.append(ind["id"])
            elif cat_meta["is_snapshot"]:
                result = fetch_snapshot(ticker)
                if result.get("value") is not None:
                    snapshots_out[ind["id"]] = result
                    chg = result.get("change_1d")
                    chg_str = f"{chg:+.3f}" if chg is not None else "—"
                    print(f"val={result['value']} 1D={chg_str} ({result['as_of']})")
                    success += 1
                else:
                    print(f"FAIL: {result.get('error', 'no value')}")
                    failed.append(ind["id"])
            else:  # event
                result = fetch_event(ticker)
                if result.get("actual") is not None:
                    indicators_out[ind["id"]] = result
                    print(f"actual={result['actual']} prior={result['prior']} ({result['release_date']})")
                    success += 1
                else:
                    print(f"FAIL: {result.get('error', 'no actual')}")
                    failed.append(ind["id"])
        except Exception as e:
            print(f"EXCEPTION: {type(e).__name__}: {e}")
            failed.append(ind["id"])

    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "stats": {"total": total, "success": success, "failed": len(failed)},
        "indicators": indicators_out,
        "snapshots": snapshots_out,
        "central_banks": cb_out,
    }
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(
        json.dumps(out, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    print()
    print(f"[bbg] {success}/{total} fetched successfully")
    print(f"[bbg] {len(indicators_out)} indicators, {len(snapshots_out)} snapshots, {len(cb_out)} CB rates")
    if failed:
        print(f"[bbg] Failed: {', '.join(failed)}")
    print(f"[bbg] Saved to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--tickers", help="Comma-separated tickers to fetch (filter)")
    args = ap.parse_args()
    filter_list = [t.strip() for t in args.tickers.split(",")] if args.tickers else None
    main(ticker_filter=filter_list)

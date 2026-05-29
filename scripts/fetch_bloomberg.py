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
import io
import json
import sys
import warnings
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

warnings.filterwarnings("ignore")

# Windows 한국어 환경(cp949)에서 unicode 글자 출력 깨짐 방지
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

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


def _bdp_fallback(ticker: str) -> dict:
    """BDH가 빈 결과를 줄 때 BDP로 최신값만 가져오는 fallback.

    historical 시계열을 못 받는 티커용. release_date는 BDP가 정확한 발표일을
    제공 안하므로 fetch 당일을 기록한다 (∴ prior/surprise는 표시 안 됨)."""
    try:
        raw = blp.bdp(ticker, "PX_LAST")
        df = _to_pandas(raw)
        if df is None or df.empty:
            return {"actual": None, "prior": None, "consensus": None, "release_date": None, "error": "bdp empty"}
        if "field" in df.columns and "value" in df.columns:
            actual = df.set_index("field")["value"].get("PX_LAST")
        elif "value" in df.columns:
            actual = df["value"].iloc[0]
        elif "PX_LAST" in df.columns:
            actual = df["PX_LAST"].iloc[0]
        else:
            actual = df.iloc[0, 0]
        if pd.isna(actual):
            return {"actual": None, "prior": None, "consensus": None, "release_date": None, "error": "bdp no value"}
        return {
            "actual": round(float(actual), 4),
            "prior": None,
            "consensus": None,
            "release_date": date.today().isoformat(),
            "source": "bdp",
        }
    except Exception as e:
        return {"actual": None, "prior": None, "consensus": None, "release_date": None, "error": f"bdp exc: {e}"}


def _parse_eco_release_dt(val) -> str | None:
    """Bloomberg ECO_RELEASE_DT는 YYYYMMDD (xbbg는 문자열 '20260508.0'로 반환) → 'YYYY-MM-DD'."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except (TypeError, ValueError):
        pass
    try:
        d = int(float(val))  # '20260508.0' → 20260508
        if d < 19000101 or d > 21000101:
            return None
        return f"{d // 10000:04d}-{(d // 100) % 100:02d}-{d % 100:02d}"
    except (ValueError, TypeError):
        return None


def fetch_event(ticker: str) -> dict:
    """Monthly/Quarterly 이벤트: 최신 actual + prior + consensus + period end + 실제 발표일.

    필드:
      PX_LAST           : 관측값
      BN_SURVEY_MEDIAN  : 애널리스트 컨센서스
      ECO_RELEASE_DT    : 실제 시장 발표일 (YYYYMMDD)
    BDH 빈 결과 시 BDP fallback (일부 티커는 historical series 미지원).
    """
    end = date.today()
    start = end - timedelta(days=540)
    raw = blp.bdh(
        ticker,
        ["PX_LAST", "BN_SURVEY_MEDIAN", "ECO_RELEASE_DT"],
        start_date=start, end_date=end,
    )
    df_raw = _to_pandas(raw)
    if df_raw is None or df_raw.empty:
        return _bdp_fallback(ticker)

    if not {"date", "field", "value"}.issubset(df_raw.columns):
        return _bdp_fallback(ticker)

    # field별로 피벗: date × {PX_LAST, BN_SURVEY_MEDIAN}
    pv = df_raw.pivot_table(index="date", columns="field", values="value", aggfunc="last")
    pv = pv.sort_index()
    if "PX_LAST" not in pv.columns:
        return {"actual": None, "prior": None, "consensus": None, "release_date": None, "error": "no PX_LAST"}

    actuals = pv["PX_LAST"].dropna()
    if actuals.empty:
        return {"actual": None, "prior": None, "consensus": None, "release_date": None, "error": "no actuals"}

    latest_date = actuals.index[-1]
    actual = float(actuals.iloc[-1])
    prior = float(actuals.iloc[-2]) if len(actuals) >= 2 else None

    consensus = None
    if "BN_SURVEY_MEDIAN" in pv.columns:
        c = pv.loc[latest_date, "BN_SURVEY_MEDIAN"]
        if pd.notna(c):
            consensus = round(float(c), 4)

    actual_release = None
    if "ECO_RELEASE_DT" in pv.columns:
        actual_release = _parse_eco_release_dt(pv.loc[latest_date, "ECO_RELEASE_DT"])

    # 다음 예정 발표일+시간 (BDP는 가장 최근 'next' 값을 반환)
    next_date, next_time = None, None
    try:
        nx = blp.bdp(ticker, ["ECO_RELEASE_DT", "ECO_RELEASE_TIME"])
        nx_df = _to_pandas(nx)
        if nx_df is not None and not nx_df.empty and "field" in nx_df.columns and "value" in nx_df.columns:
            npv = nx_df.set_index("field")["value"]
            nd = npv.get("ECO_RELEASE_DT")
            if nd is not None and not (isinstance(nd, float) and pd.isna(nd)):
                next_date = str(nd)[:10]  # 'YYYY-MM-DD'
            nt = npv.get("ECO_RELEASE_TIME")
            if nt is not None and not (isinstance(nt, float) and pd.isna(nt)):
                next_time = str(nt)[:5]   # 'HH:MM'
    except Exception:
        pass

    return {
        "actual": round(actual, 4),
        "prior": round(prior, 4) if prior is not None else None,
        "consensus": consensus,
        "release_date": pd.Timestamp(latest_date).strftime("%Y-%m-%d"),  # period end
        "actual_release_date": actual_release,                            # 실제 시장 발표일
        "next_release_date": next_date,                                   # 다음 발표 예정일 (KST)
        "next_release_time": next_time,                                   # 다음 발표 예정 시간 (KST HH:MM)
    }


def _bdp_value(ticker: str, field: str) -> float | None:
    """단일 ticker × field 값 추출 헬퍼."""
    try:
        raw = blp.bdp(ticker, field)
        df = _to_pandas(raw)
        if df is None or df.empty:
            return None
        if "field" in df.columns and "value" in df.columns:
            v = df.set_index("field")["value"].get(field)
        elif "value" in df.columns:
            v = df["value"].iloc[0]
        elif field in df.columns:
            v = df[field].iloc[0]
        else:
            v = df.iloc[0, 0]
        return float(v) if v is not None and pd.notna(v) else None
    except Exception:
        return None


def fetch_cb_rate(ticker: str, ois_ticker: str | None = None) -> dict:
    """중앙은행 정책금리:
       - rate           : PX_LAST 현재 정책금리
       - consensus_rate : BN_SURVEY_MEDIAN 다음 회의 애널리스트 컨센서스
       - implied_1y     : 1Y OIS 평균금리 (12개월 implied path proxy)
    """
    raw = blp.bdp(ticker, ["PX_LAST", "BN_SURVEY_MEDIAN"])
    df = _to_pandas(raw)
    if df is None or df.empty:
        return {"rate": None, "consensus_rate": None, "implied_1y": None, "next_meeting": None, "error": "empty"}

    if "field" in df.columns and "value" in df.columns:
        pv = df.set_index("field")["value"]
        rate = pv.get("PX_LAST")
        cons = pv.get("BN_SURVEY_MEDIAN")
    else:
        rate = df.get("PX_LAST", pd.Series([None])).iloc[0]
        cons = df.get("BN_SURVEY_MEDIAN", pd.Series([None])).iloc[0]

    if pd.isna(rate):
        return {"rate": None, "consensus_rate": None, "implied_1y": None, "next_meeting": None, "error": "no rate"}

    implied = _bdp_value(ois_ticker, "PX_LAST") if ois_ticker else None

    return {
        "rate": round(float(rate), 4),
        "consensus_rate": round(float(cons), 4) if cons is not None and pd.notna(cons) else None,
        "implied_1y": round(implied, 4) if implied is not None else None,
        "next_meeting": None,  # 캘린더에서 채움
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
                result = fetch_cb_rate(ticker, ind.get("ois_1y_bbg"))
                if result.get("rate") is not None:
                    cb_out[ind["id"]] = result
                    cons = result.get("consensus_rate")
                    imp = result.get("implied_1y")
                    extras = []
                    if cons is not None: extras.append(f"cons={cons}")
                    if imp is not None:  extras.append(f"1Y OIS={imp}")
                    extra_str = " " + " ".join(extras) if extras else ""
                    print(f"rate={result['rate']}%{extra_str}")
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
                    cons = result.get("consensus")
                    cons_str = f"cons={cons}" if cons is not None else "cons=-"
                    print(f"act={result['actual']} {cons_str} prior={result['prior']} ({result['release_date']})")
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

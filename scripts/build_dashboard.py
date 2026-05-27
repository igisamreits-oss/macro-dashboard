"""
정적 대시보드 빌더.

data/bloomberg/latest.json, data/fred/latest.json, data/calendar/latest.json 을 읽어
templates/index.html.j2 로 docs/index.html 을 생성한다.

데이터 파일이 없으면 샘플로 채워서 UI 검증부터 가능.

Usage:
    python scripts/build_dashboard.py
    python scripts/build_dashboard.py --sample
"""
from __future__ import annotations

import argparse
import json
import random
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "docs"

KST = timezone(timedelta(hours=9))

MONTH_SHORT = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
FREQ_LABEL = {"D": "Daily", "W": "Weekly", "M": "Monthly", "Q": "Quarterly", "E": "Event"}


def period_label(date_str: str | None, frequency: str) -> str:
    """발표일 → 데이터가 다루는 기간 라벨 ('Apr 2026', 'Q1 2026', 등)."""
    if not date_str:
        return ""
    try:
        d = date.fromisoformat(date_str)
    except (ValueError, TypeError):
        return date_str
    if frequency == "M":
        return f"{MONTH_SHORT[d.month]} {d.year}"
    if frequency == "Q":
        q = (d.month - 1) // 3 + 1
        return f"Q{q} {d.year}"
    if frequency == "W":
        return f"Wk {d.strftime('%m/%d')}"
    if frequency == "D":
        return d.strftime("%m/%d")
    return d.isoformat()


# ── Data loading ─────────────────────────────────────────────────────
def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_all_data() -> dict:
    return {
        "bloomberg": load_json(DATA_DIR / "bloomberg" / "latest.json") or {},
        "fred":      load_json(DATA_DIR / "fred" / "latest.json") or {},
        "calendar":  load_json(DATA_DIR / "calendar" / "latest.json") or {},
    }


# ── Sample data (UI 검증용) ───────────────────────────────────────────
def sample_data() -> dict:
    today = date.today()
    rng = random.Random(42)

    def d(offset: int) -> str:
        return (today + timedelta(days=offset)).isoformat()

    # 모든 지표에 합리적 placeholder 값 생성
    indicators: dict[str, dict] = {}
    snapshots: dict[str, dict] = {}
    cb_data: dict[str, dict] = {}

    for ind in config.INDICATORS:
        cat = ind["category"]
        cat_meta = config.CATEGORIES[cat]

        if cat == "central_bank":
            cb_data[ind["id"]] = {
                "rate": round(rng.uniform(0.25, 5.5), 2),
                "next_meeting": d(rng.randint(2, 25)),
                "consensus_rate": None,
            }
        elif cat_meta["is_snapshot"]:
            base = {
                "policy_rate":   rng.uniform(0.5, 5.5),
                "credit_spread": rng.uniform(0.6, 2.0),
                "breakeven":     rng.uniform(1.5, 3.0),
                "mortgage_rate": rng.uniform(6.0, 7.5),
            }[cat]
            snapshots[ind["id"]] = {
                "value": round(base, ind.get("decimals", 2)),
                "change_1d": round(rng.uniform(-0.05, 0.05), 2),
                "as_of": d(0),
            }
        else:  # 이벤트형 (물가/실업/주택/소비/소매)
            base_value = {
                "inflation":           rng.uniform(2.0, 4.0),
                "unemployment":        rng.uniform(3.0, 6.0),
                "housing":             rng.uniform(-2.0, 10.0),
                "consumer_confidence": rng.uniform(40, 110),
                "retail_sales":        rng.uniform(-0.5, 1.5),
            }[cat]
            consensus = base_value + rng.uniform(-0.3, 0.3)
            indicators[ind["id"]] = {
                "actual": round(base_value, ind.get("decimals", 1)),
                "consensus": round(consensus, ind.get("decimals", 1)),
                "prior": round(base_value + rng.uniform(-0.3, 0.3), ind.get("decimals", 1)),
                "release_date": d(-rng.randint(1, 14)),
            }

    return {
        "bloomberg": {
            "indicators": indicators,
            "snapshots": snapshots,
            "central_banks": cb_data,
        },
        "calendar": {
            "events": [
                {"date": d(-3), "country": "US", "indicator_id": "us_cpi_yoy",      "time_kst": "21:30"},
                {"date": d(-2), "country": "CA", "indicator_id": "ca_cpi_yoy",      "time_kst": "21:30"},
                {"date": d(2),  "country": "CA", "indicator_id": "boc",             "time_kst": "22:45"},
                {"date": d(6),  "country": "AU", "indicator_id": "rba",             "time_kst": "13:30"},
                {"date": d(8),  "country": "US", "indicator_id": "fomc",            "time_kst": "03:00"},
                {"date": d(15), "country": "EU", "indicator_id": "ecb",             "time_kst": "21:15"},
            ],
        },
    }


# ── Calendar grid ────────────────────────────────────────────────────
WEEKDAY_KO = ["월", "화", "수", "목", "금", "토", "일"]


def build_calendar(events: list[dict], today: date) -> dict:
    start = today - timedelta(days=7)
    end = today + timedelta(days=28)

    days = []
    cur = start
    while cur <= end:
        days.append({
            "date": cur.isoformat(),
            "label": cur.strftime("%m/%d"),
            "weekday": WEEKDAY_KO[cur.weekday()],
            "is_today": cur == today,
            "is_weekend": cur.weekday() >= 5,
            "is_past": cur < today,
        })
        cur += timedelta(days=1)

    events_by_country_day: dict[str, dict[str, list[dict]]] = {}
    for ev in events:
        ind = config.get_indicator(ev["indicator_id"])
        if not ind:
            continue
        country = ev["country"]
        day = ev["date"]
        country_meta = config.COUNTRIES.get(country, {})
        cat_meta = config.CATEGORIES.get(ind["category"], {})
        events_by_country_day.setdefault(country, {}).setdefault(day, []).append({
            "name": ind["name"],
            "name_ko": ind["name_ko"],
            "short_name": ind["name_ko"] or ind["name"],
            "importance": ind["importance"],
            "time_kst": ev.get("time_kst", ""),
            "note": ev.get("note", ""),
            "country_code": country,
            "country_name": country_meta.get("name", country),
            "country_flag": country_meta.get("flag", ""),
            "category": ind["category"],
            "category_ko": cat_meta.get("name_ko", ind["category"]),
            "category_emoji": cat_meta.get("emoji", ""),
            "date": day,
            "is_past": date.fromisoformat(day) < today,
        })

    return {
        "days": days,
        "events_by_country_day": events_by_country_day,
        "range_label": f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}",
    }


# ── Event-category panels (Inflation / Unemployment / Housing / Consumer / Retail) ──
def build_event_categories(indicators_data: dict) -> dict[str, dict]:
    """이벤트형 카테고리별 { by_country: {country: [rows]} } 구조 생성."""
    result: dict[str, dict] = {}
    for cat_id in config.event_categories():
        if cat_id == "central_bank":
            continue  # CB는 별도 카드 섹션
        cat_meta = config.CATEGORIES[cat_id]
        by_country: dict[str, list[dict]] = {}

        for ind in config.by_category(cat_id):
            d_ = indicators_data.get(ind["id"], {})
            actual = d_.get("actual")
            consensus = d_.get("consensus")
            surprise = None
            if actual is not None and consensus is not None:
                surprise = round(actual - consensus, 2)
            freq = ind.get("frequency", "M")
            row = {
                "id": ind["id"],
                "name": ind["name"],
                "name_ko": ind["name_ko"],
                "actual": actual,
                "consensus": consensus,
                "prior": d_.get("prior"),
                "surprise": surprise,
                "release_date": d_.get("release_date"),
                "period": period_label(d_.get("release_date"), freq),
                "frequency": freq,
                "freq_label": FREQ_LABEL.get(freq, freq),
                "importance": ind["importance"],
                "unit": ind.get("unit", "%"),
                "decimals": ind.get("decimals", 1),
            }
            by_country.setdefault(ind["country"], []).append(row)

        result[cat_id] = {
            "name_ko": cat_meta["name_ko"],
            "emoji": cat_meta["emoji"],
            "by_country": by_country,
        }
    return result


# ── Markets snapshot (Daily/Weekly snapshot indicators) ──────────────
def build_markets(snapshot_data: dict) -> dict[str, dict]:
    """스냅샷형 카테고리별 { rows: [...] } 구조."""
    result: dict[str, dict] = {}
    for cat_id in config.snapshot_categories():
        cat_meta = config.CATEGORIES[cat_id]
        rows = []
        for ind in config.by_category(cat_id):
            d_ = snapshot_data.get(ind["id"], {})
            country_meta = config.COUNTRIES.get(ind["country"], {})
            freq = ind.get("frequency", "D")
            rows.append({
                "id": ind["id"],
                "name": ind["name"],
                "name_ko": ind["name_ko"],
                "flag": country_meta.get("flag", ""),
                "country_code": ind["country"],
                "value": d_.get("value"),
                "change_1d": d_.get("change_1d"),
                "as_of": d_.get("as_of"),
                "frequency": freq,
                "freq_label": FREQ_LABEL.get(freq, freq),
                "unit": ind.get("unit", "%"),
                "decimals": ind.get("decimals", 2),
            })
        result[cat_id] = {
            "name_ko": cat_meta["name_ko"],
            "emoji": cat_meta["emoji"],
            "rows": rows,
        }
    return result


# ── Central bank cards ───────────────────────────────────────────────
def build_central_banks(cb_data: dict, today: date, events: list[dict]) -> list[dict]:
    next_meeting_by_cb: dict[str, str] = {}
    for ev in sorted(events, key=lambda e: e["date"]):
        if date.fromisoformat(ev["date"]) < today:
            continue
        cb_id = ev["indicator_id"]
        if cb_id not in next_meeting_by_cb:
            ind = config.get_indicator(cb_id)
            if ind and ind["category"] == "central_bank":
                next_meeting_by_cb[cb_id] = ev["date"]

    cards = []
    for ind in config.INDICATORS:
        if ind["category"] != "central_bank":
            continue
        d_ = cb_data.get(ind["id"], {})
        next_meeting = next_meeting_by_cb.get(ind["id"]) or d_.get("next_meeting")
        is_imminent = False
        if next_meeting:
            try:
                days_to = (date.fromisoformat(next_meeting) - today).days
                is_imminent = 0 <= days_to <= 7
            except ValueError:
                pass
        rate = d_.get("rate")
        implied = d_.get("implied_1y")
        delta_bp = None
        moves = None
        if rate is not None and implied is not None:
            delta_bp = round((implied - rate) * 100)  # %p → bp
            moves = round(delta_bp / 25, 1)            # 25bp = 1 move

        cards.append({
            "id": ind["id"],
            "name": ind["name"],
            "name_ko": ind["name_ko"],
            "country": ind["country"],
            "flag": config.COUNTRIES[ind["country"]]["flag"],
            "rate": rate,
            "consensus_rate": d_.get("consensus_rate"),
            "implied_1y": implied,
            "implied_delta_bp": delta_bp,
            "implied_moves": moves,
            "next_meeting": next_meeting,
            "is_imminent": is_imminent,
        })
    return cards


# ── Main ─────────────────────────────────────────────────────────────
def main(use_sample: bool = False) -> None:
    today = date.today()

    real = load_all_data()
    have_real = bool(real["bloomberg"]) or bool(real["fred"]) or bool(real["calendar"])

    if use_sample or not have_real:
        data = sample_data()
        print("[build] Using sample data" + (" (--sample flag)" if use_sample else ""))
    else:
        # 샘플을 베이스로 깔고 실데이터로 덮어쓰기
        data = sample_data()
        bbg = real.get("bloomberg", {})
        for k, v in bbg.get("indicators", {}).items():
            data["bloomberg"]["indicators"][k] = v
        for k, v in bbg.get("snapshots", {}).items():
            data["bloomberg"]["snapshots"][k] = v
        for k, v in bbg.get("central_banks", {}).items():
            data["bloomberg"]["central_banks"][k] = v
        if real.get("calendar", {}).get("events"):
            data["calendar"] = real["calendar"]
        print("[build] Real data merged (sample fallback for missing slots)")

    indicators_data = data["bloomberg"]["indicators"]
    snapshot_data = data["bloomberg"]["snapshots"]
    cb_data = data["bloomberg"]["central_banks"]
    events = data["calendar"]["events"]

    # FRED 덮어쓰기 (US 우선)
    fred_inds = real.get("fred", {}).get("indicators", {})
    for k, v in fred_inds.items():
        if v.get("actual") is not None:
            indicators_data[k] = v

    fred_cb = real.get("fred", {}).get("central_banks", {})
    for k, v in fred_cb.items():
        if v.get("rate") is not None:
            cb_data[k] = {**cb_data.get(k, {}), "rate": v["rate"], "source": "fred"}

    ctx = {
        "build_time": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "countries": config.COUNTRIES,
        "categories": config.CATEGORIES,
        "calendar": build_calendar(events, today),
        "markets": build_markets(snapshot_data),
        "event_categories": build_event_categories(indicators_data),
        "central_banks": build_central_banks(cb_data, today, events),
    }

    env = Environment(
        loader=FileSystemLoader(TEMPLATE_DIR),
        autoescape=select_autoescape(["html", "xml"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    tmpl = env.get_template("index.html.j2")
    html = tmpl.render(**ctx)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUTPUT_DIR / "index.html"
    out.write_text(html, encoding="utf-8")
    print(f"[build] Wrote {out} ({len(html):,} bytes)")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="Force sample data")
    args = ap.parse_args()
    main(use_sample=args.sample)

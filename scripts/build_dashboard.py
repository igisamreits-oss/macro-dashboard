"""
정적 대시보드 빌더.

data/bloomberg/*.json, data/fred/*.json, data/calendar/*.json 을 읽어
templates/index.html.j2 로 docs/index.html 을 생성한다.

데이터 파일이 없으면 샘플 데이터로 빌드해서 UI 검증부터 가능하게 한다.

Usage:
    python scripts/build_dashboard.py
    python scripts/build_dashboard.py --sample   # 샘플 데이터 강제
"""
from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

import config

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
TEMPLATE_DIR = ROOT / "templates"
OUTPUT_DIR = ROOT / "docs"

KST = timezone(timedelta(hours=9))


# ── Data loading ─────────────────────────────────────────────────────
def load_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def load_all_data() -> dict:
    """Bloomberg latest.json > FRED > 샘플 순으로 머지."""
    bbg = load_json(DATA_DIR / "bloomberg" / "latest.json") or {}
    fred = load_json(DATA_DIR / "fred" / "latest.json") or {}
    cal = load_json(DATA_DIR / "calendar" / "latest.json") or {}
    return {"bloomberg": bbg, "fred": fred, "calendar": cal}


# ── Sample data (UI 검증용) ───────────────────────────────────────────
def sample_data() -> dict:
    today = date.today()

    def d(offset: int) -> str:
        return (today + timedelta(days=offset)).isoformat()

    return {
        "bloomberg": {
            "indicators": {
                "us_cpi_yoy":      {"actual": 3.2, "consensus": 3.3, "prior": 3.4, "release_date": d(-3)},
                "us_core_cpi_yoy": {"actual": 3.8, "consensus": 3.9, "prior": 4.0, "release_date": d(-3)},
                "us_pce_yoy":      {"actual": 2.6, "consensus": 2.6, "prior": 2.7, "release_date": d(-1)},
                "us_core_pce_yoy": {"actual": 2.8, "consensus": 2.8, "prior": 2.9, "release_date": d(-1)},
                "eu_hicp_yoy":     {"actual": 2.4, "consensus": 2.5, "prior": 2.6, "release_date": d(-5)},
                "eu_core_hicp_yoy":{"actual": 2.9, "consensus": 2.9, "prior": 3.1, "release_date": d(-5)},
                "uk_cpi_yoy":      {"actual": 3.4, "consensus": 3.5, "prior": 3.2, "release_date": d(-2)},
                "jp_cpi_yoy":      {"actual": 2.5, "consensus": 2.4, "prior": 2.3, "release_date": d(-4)},
                "jp_core_cpi":     {"actual": 2.2, "consensus": 2.2, "prior": 2.0, "release_date": d(-4)},
                "au_cpi_yoy_q":    {"actual": 3.4, "consensus": 3.5, "prior": 3.6, "release_date": d(-6)},
                "ca_cpi_yoy":      {"actual": 2.0, "consensus": 2.1, "prior": 2.4, "release_date": d(-2)},
                "sg_cpi_yoy":      {"actual": 2.7, "consensus": 2.8, "prior": 2.9, "release_date": d(-7)},
            },
            "central_banks": {
                "fomc": {"rate": 5.50, "next_meeting": d(8),  "consensus_rate": 5.25},
                "ecb":  {"rate": 3.50, "next_meeting": d(15), "consensus_rate": 3.25},
                "boe":  {"rate": 5.00, "next_meeting": d(11), "consensus_rate": 4.75},
                "boj":  {"rate": 0.25, "next_meeting": d(20), "consensus_rate": 0.25},
                "rba":  {"rate": 4.35, "next_meeting": d(6),  "consensus_rate": 4.10},
                "boc":  {"rate": 4.25, "next_meeting": d(2),  "consensus_rate": 4.00},
                "mas":  {"rate": None, "next_meeting": d(25), "consensus_rate": None},
            },
        },
        "calendar": {
            "events": [
                {"date": d(-5), "country": "EU", "indicator_id": "eu_hicp_yoy",     "time_kst": "18:00"},
                {"date": d(-3), "country": "US", "indicator_id": "us_cpi_yoy",      "time_kst": "21:30"},
                {"date": d(-2), "country": "CA", "indicator_id": "ca_cpi_yoy",      "time_kst": "21:30"},
                {"date": d(-1), "country": "US", "indicator_id": "us_pce_yoy",      "time_kst": "21:30"},
                {"date": d(2),  "country": "CA", "indicator_id": "boc",             "time_kst": "22:45"},
                {"date": d(4),  "country": "JP", "indicator_id": "jp_tokyo_cpi",    "time_kst": "08:30"},
                {"date": d(6),  "country": "AU", "indicator_id": "rba",             "time_kst": "13:30"},
                {"date": d(8),  "country": "US", "indicator_id": "fomc",            "time_kst": "03:00"},
                {"date": d(11), "country": "UK", "indicator_id": "boe",             "time_kst": "20:00"},
                {"date": d(13), "country": "US", "indicator_id": "us_cpi_yoy",      "time_kst": "21:30"},
                {"date": d(15), "country": "EU", "indicator_id": "ecb",             "time_kst": "22:15"},
                {"date": d(17), "country": "JP", "indicator_id": "jp_cpi_yoy",      "time_kst": "08:30"},
                {"date": d(20), "country": "JP", "indicator_id": "boj",             "time_kst": "12:00"},
                {"date": d(22), "country": "AU", "indicator_id": "au_cpi_yoy_m",    "time_kst": "10:30"},
                {"date": d(25), "country": "SG", "indicator_id": "mas",             "time_kst": "08:00"},
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

    # group events by (country, date)
    events_by_country_day: dict[str, dict[str, list[dict]]] = {}
    for ev in events:
        ind = config.get_indicator(ev["indicator_id"])
        if not ind:
            continue
        country = ev["country"]
        day = ev["date"]
        events_by_country_day.setdefault(country, {}).setdefault(day, []).append({
            "name": ind["name"],
            "short_name": ind["name_ko"] or ind["name"],
            "importance": ind["importance"],
            "time_kst": ev.get("time_kst", ""),
            "is_past": date.fromisoformat(day) < today,
        })

    return {
        "days": days,
        "events_by_country_day": events_by_country_day,
        "range_label": f"{start.strftime('%Y-%m-%d')} ~ {end.strftime('%Y-%m-%d')}",
    }


# ── Inflation snapshot ───────────────────────────────────────────────
def build_inflation_snapshot(indicators_data: dict) -> dict[str, list[dict]]:
    by_country: dict[str, list[dict]] = {}
    for ind in config.INDICATORS:
        if ind["category"] != "inflation":
            continue
        d = indicators_data.get(ind["id"], {})
        actual = d.get("actual")
        consensus = d.get("consensus")
        surprise = None
        if actual is not None and consensus is not None:
            surprise = round(actual - consensus, 2)

        row = {
            "id": ind["id"],
            "name": ind["name"],
            "name_ko": ind["name_ko"],
            "actual": actual,
            "consensus": consensus,
            "prior": d.get("prior"),
            "surprise": surprise,
            "release_date": d.get("release_date"),
            "importance": ind["importance"],
        }
        by_country.setdefault(ind["country"], []).append(row)
    return by_country


# ── Central bank cards ───────────────────────────────────────────────
def build_central_banks(cb_data: dict, today: date) -> list[dict]:
    cards = []
    for ind in config.INDICATORS:
        if ind["category"] != "central_bank":
            continue
        d = cb_data.get(ind["id"], {})
        next_meeting = d.get("next_meeting")
        is_imminent = False
        if next_meeting:
            try:
                days_to = (date.fromisoformat(next_meeting) - today).days
                is_imminent = 0 <= days_to <= 7
            except ValueError:
                pass

        cards.append({
            "id": ind["id"],
            "name": ind["name"],
            "name_ko": ind["name_ko"],
            "country": ind["country"],
            "flag": config.COUNTRIES[ind["country"]]["flag"],
            "rate": d.get("rate"),
            "consensus_rate": d.get("consensus_rate"),
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
        # 샘플을 베이스로 깔고 실데이터로 덮어쓰기 (MVP 단계: 다른 fetcher 미구현 슬롯은 샘플 유지)
        data = sample_data()
        bbg = real.get("bloomberg", {})
        for k, v in bbg.get("indicators", {}).items():
            data["bloomberg"]["indicators"][k] = v
        for k, v in bbg.get("central_banks", {}).items():
            data["bloomberg"]["central_banks"][k] = v
        if real.get("calendar", {}).get("events"):
            data["calendar"] = real["calendar"]
        print("[build] Loaded real data (sample fallback for missing slots)")

    indicators_data = data["bloomberg"]["indicators"]
    cb_data = data["bloomberg"]["central_banks"]
    events = data["calendar"]["events"]

    # FRED는 항상 마지막에 덮어쓰기 (US 우선)
    fred_inds = real.get("fred", {}).get("indicators", {})
    for k, v in fred_inds.items():
        if v.get("actual") is not None:
            indicators_data[k] = v

    fred_cb = real.get("fred", {}).get("central_banks", {})
    for k, v in fred_cb.items():
        if v.get("rate") is not None:
            # FRED은 rate만 덮어씀 — next_meeting은 샘플/캘린더에서 유지
            cb_data[k] = {**cb_data.get(k, {}), "rate": v["rate"], "source": "fred"}

    ctx = {
        "build_time": datetime.now(KST).strftime("%Y-%m-%d %H:%M"),
        "countries": config.COUNTRIES,
        "categories": config.CATEGORIES,
        "calendar": build_calendar(events, today),
        "inflation_by_country": build_inflation_snapshot(indicators_data),
        "central_banks": build_central_banks(cb_data, today),
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

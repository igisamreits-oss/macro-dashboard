"""
Goldman Sachs Marquee 리서치 피드 스크래퍼.

저장된 chrome-profile/ 세션으로 marquee.gs.com 접속 → /v1/content/feed?limit=40 호출 가로채기.
returns: totalResults + results[] (documentId/title/synopsis/authors)

결과: data/research/gs_latest.json
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILE_DIR = ROOT / "chrome-profile"
OUT_DIR = ROOT / "data" / "research"
OUT_DIR.mkdir(parents=True, exist_ok=True)
OUT_PATH = OUT_DIR / "gs_latest.json"

GS_HOME = "https://marquee.gs.com/s/home"
GS_FEED_KEY = "content/feed"


def close_chrome() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(2)


def fetch_gs() -> list[dict]:
    close_chrome()
    captured = {"data": None}

    def on_response(response):
        if GS_FEED_KEY in response.url and "limit=40" in response.url and response.status == 200:
            try:
                captured["data"] = response.json()
            except Exception:
                pass

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=True,
            viewport={"width": 1400, "height": 900},
            args=["--profile-directory=Default", "--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        page.on("response", on_response)
        try:
            page.goto(GS_HOME, wait_until="domcontentloaded", timeout=60000)
            for _ in range(30):
                if captured["data"] is not None:
                    break
                time.sleep(1)
            if captured["data"] is None:
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                time.sleep(5)
        except Exception as e:
            print(f"[gs] page nav warn: {e}")
        finally:
            ctx.close()

    if captured["data"] is None:
        print("[gs] feed not captured")
        return []

    results = captured["data"].get("results", []) or []
    print(f"[gs] {len(results)} documents captured")

    items = []
    for r in results:
        doc_url = r.get("documentUrl") or ""
        publish_date = None
        parts = doc_url.split("/")
        for i, p in enumerate(parts):
            if p.isdigit() and len(p) == 4 and i + 2 < len(parts):
                try:
                    y, m, dd = parts[i], parts[i + 1], parts[i + 2]
                    publish_date = f"{y}-{m}-{dd}"
                    break
                except Exception:
                    pass

        authors = []
        for a in r.get("authors", []) or []:
            authors.append({
                "name": a.get("displayName"),
                "department": a.get("departmentName"),
                "division": a.get("division"),
            })

        items.append({
            "platform": "GS",
            "doc_id": r.get("documentId"),
            "title": (r.get("title") or "").strip(),
            "summary": (r.get("synopsis") or "").strip(),
            "link": f"https://marquee.gs.com{doc_url}" if doc_url else None,
            "authors": authors,
            "tags": list({a.get("department") for a in authors if a.get("department")}),
            "publish_time": publish_date,
        })
    return items


def main() -> None:
    items = fetch_gs()
    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[gs] Saved {len(items)} items to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

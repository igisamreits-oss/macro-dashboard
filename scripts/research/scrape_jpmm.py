"""
JPMM 리서치 피드 스크래퍼.

저장된 chrome-profile/ 세션으로 markets.jpmorgan.com 접속 → research/multimedia/related-content 가로채기.
응답: { data: { <publicationId>: [docs...] } } — 사용자의 follow된 publication별 최근 documents.

최근 14일 내 문서만 필터 (전체 endpoint dump는 ~7천개).
결과: data/research/jpmm_latest.json
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
OUT_PATH = OUT_DIR / "jpmm_latest.json"

JPMM_SECTORS = "https://markets.jpmorgan.com/jpmm/research.browse_sector_page"
ENDPOINT_KEY = "research/multimedia/related-content"


def close_chrome() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(2)


def fetch_jpmm() -> list[dict]:
    close_chrome()
    captured = {"data": None}

    def on_response(response):
        if ENDPOINT_KEY in response.url and response.status == 200:
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
            page.goto(JPMM_SECTORS, wait_until="domcontentloaded", timeout=60000)
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
            print(f"[jpmm] page nav warn: {e}")
        finally:
            ctx.close()

    if captured["data"] is None:
        print("[jpmm] endpoint not captured")
        return []

    now_ms = int(datetime.now(tz=timezone.utc).timestamp() * 1000)
    cutoff_ms = now_ms - 14 * 24 * 3600 * 1000

    items: list[dict] = []
    data_block = captured["data"].get("data", {}) or {}
    for pub_id, docs in data_block.items():
        for d in (docs or []):
            pub_ts = d.get("publicationDate")
            if not pub_ts or int(pub_ts) < cutoff_ms:
                continue
            try:
                pub_date = datetime.fromtimestamp(int(pub_ts) / 1000, tz=timezone.utc).strftime("%Y-%m-%d")
            except Exception:
                continue
            analysts = []
            for a in d.get("analysts", []) or []:
                analysts.append({
                    "name": a.get("displayName") or f"{a.get('firstName','')} {a.get('lastName','')}".strip(),
                    "team": a.get("teamName"),
                    "email": a.get("email"),
                })
            doc_id = d.get("documentId") or d.get("id")
            link = None
            if doc_id:
                link = f"https://markets.jpmorgan.com/research/open?documentId={doc_id}"
            items.append({
                "platform": "JPM",
                "doc_id": doc_id,
                "publication_id": pub_id,
                "title": (d.get("title") or "").strip(),
                "summary": (d.get("subTitle") or d.get("abstract") or "").strip(),
                "link": link,
                "authors": analysts,
                "tags": list({a.get("team") for a in analysts if a.get("team")}),
                "publish_time": pub_date,
            })

    seen = set()
    unique = []
    for i in items:
        k = i.get("doc_id")
        if not k or k in seen:
            continue
        seen.add(k)
        unique.append(i)

    print(f"[jpmm] {len(unique)} unique documents (from {len(items)} raw)")
    return unique


def main() -> None:
    items = fetch_jpmm()
    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[jpmm] Saved {len(items)} items to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

"""
Citi Velocity 리서치 피드 스크래퍼.

Playwright context로 인증된 API 직접 호출 (cookies는 chrome-profile/에 저장됨).
endpoint: /cvr/curationws/eppublic/V1/currentweekrecenthighlights.json
이번 주 큐레이션된 Citi 리서치 문서 리스트 반환.

결과: data/research/latest.json
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
OUT_PATH = OUT_DIR / "latest.json"

CITI_API = "https://www.citivelocity.com/cvr/curationws/eppublic/V1/currentweekrecenthighlights.json?platformId=79"
CITI_HOME = "https://www.citivelocity.com/cv2/go/RSCH_LANDING_PAGE"


def close_chrome() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(2)


def fetch_citi() -> list[dict]:
    """Playwright context로 페이지 로드 + API 응답 가로채기.

    페이지의 JS가 API를 호출할 때 모든 필요 헤더(CSRF 토큰 등)가 자동 포함됨.
    우리는 그 응답을 listener로 캡처.
    """
    close_chrome()
    captured = {"data": None}

    def on_response(response):
        if "currentweekrecenthighlights.json" in response.url and response.status == 200:
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
            page.goto(CITI_HOME, wait_until="domcontentloaded", timeout=60000)
            # 페이지의 JS가 API 호출하기까지 충분히 대기
            for _ in range(20):
                if captured["data"] is not None:
                    break
                time.sleep(1)
            # 그래도 안 잡히면 networkidle까지 추가 대기
            if captured["data"] is None:
                try:
                    page.wait_for_load_state("networkidle", timeout=20000)
                except Exception:
                    pass
                time.sleep(5)
        except Exception as e:
            print(f"[citi] page nav warn: {e}")
        finally:
            ctx.close()

    if captured["data"] is None:
        print("[citi] API response not captured")
        return []

    docs = captured["data"].get("documents", []) or []
    print(f"[citi] {len(docs)} documents captured from API")

    items = []
    for d in docs:
        items.append({
            "platform": "Citi",
            "doc_id": d.get("docId"),
            "title": (d.get("title") or "").strip(),
            "summary": (d.get("summary") or "").strip(),
            "link": d.get("docLink"),
            "tags": [t.strip() for t in (d.get("tags") or "").split(",") if t.strip()],
            "publish_time": _parse_yyyymmddhhmmss(d.get("docPublishTime")),
            "thumbnail": d.get("thumbnailURL"),
        })
    return items


def _parse_yyyymmddhhmmss(s: str | None) -> str | None:
    """20260608190233 → '2026-06-08 19:02'."""
    if not s or len(str(s)) < 8:
        return None
    s = str(s)
    try:
        y, m, d = s[:4], s[4:6], s[6:8]
        if len(s) >= 12:
            return f"{y}-{m}-{d} {s[8:10]}:{s[10:12]}"
        return f"{y}-{m}-{d}"
    except Exception:
        return None


def main() -> None:
    items = fetch_citi()
    out = {
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "items": items,
    }
    OUT_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"[citi] Saved {len(items)} items to {OUT_PATH.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

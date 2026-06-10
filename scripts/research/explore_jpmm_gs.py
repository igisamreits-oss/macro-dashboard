"""
JPMM + GS Marquee 탐색 — Citi에서 통한 response listener 기법 재시도.

각 사이트 홈 + 가능한 research 경로에 접속하면서 JSON API 응답을 모두 캡처.
어디서 리포트 리스트를 가져오는지 파악.
"""
from __future__ import annotations

import io
import json
import subprocess
import sys
import time
from pathlib import Path

if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parent.parent.parent
PROFILE_DIR = ROOT / "chrome-profile"
OUT_DIR = ROOT / "research-screenshots"
OUT_DIR.mkdir(exist_ok=True)


SKIP_PATTERNS = [
    "cookieconsent", "onetrust", "go-mpulse", "glassbox", "qualtrics",
    "doubleclick", "google-analytics", "googletagmanager", "adobedtm",
    "metrics", "tracking", "telemetry", "/recaptcha/",
]


def is_interesting(url: str) -> bool:
    if not url:
        return False
    low = url.lower()
    return not any(s in low for s in SKIP_PATTERNS)


def explore_site(ctx, label: str, url: str, wait_seconds: int = 18) -> dict:
    print(f"\n=== {label} ===")
    print(f"  URL: {url}")

    captured: list[dict] = []

    def on_response(response):
        u = response.url
        ct = response.headers.get("content-type", "") or ""
        if "json" not in ct.lower():
            return
        if not is_interesting(u):
            return
        body = ""
        try:
            body = response.text()[:2000]
        except Exception:
            pass
        post_data = None
        try:
            post_data = response.request.post_data
            if post_data and len(post_data) > 400:
                post_data = post_data[:400] + "..."
        except Exception:
            pass
        captured.append({
            "url": u,
            "method": response.request.method,
            "status": response.status,
            "post_data": post_data,
            "body_preview": body[:1500],
        })

    page = ctx.new_page()
    page.on("response", on_response)

    info: dict = {"input_url": url}
    try:
        page.goto(url, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=30000)
        except Exception:
            pass
        time.sleep(wait_seconds)
        info["final_url"] = page.url
        info["title"] = page.title()
        info["frame_count"] = len(page.frames)
        info["frame_urls"] = [f.url for f in page.frames][:15]
        body = page.evaluate("() => document.body && document.body.innerText || ''")
        info["body_preview"] = body[:1500]
        # 페이지 내 의미있는 링크
        links = []
        for a in page.locator("a[href]").all()[:200]:
            try:
                href = a.get_attribute("href") or ""
                txt = (a.inner_text() or "").strip()[:120]
                if href and txt and not href.startswith("#") and "javascript:" not in href:
                    links.append({"text": txt, "href": href})
            except Exception:
                pass
        info["links"] = links[:60]
        page.screenshot(path=str(OUT_DIR / f"{label}.png"), full_page=False)
    except Exception as e:
        info["error"] = str(e)[:300]
    finally:
        page.close()

    info["api_responses"] = captured
    print(f"  Frames: {info.get('frame_count', '?')}")
    print(f"  Links: {len(info.get('links', []))}")
    print(f"  API JSON (interesting): {len(captured)}")
    return info


def main() -> None:
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(2)

    targets = [
        ("jpmm_home",   "https://markets.jpmorgan.com/jpmm"),
        ("jpmm_sectors","https://markets.jpmorgan.com/jpmm/research.browse_sector_page"),
        ("gs_home",     "https://marquee.gs.com/s/home"),
        ("gs_research", "https://marquee.gs.com/s/research"),
    ]
    results = {}

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=True,
            viewport={"width": 1400, "height": 900},
            args=["--profile-directory=Default", "--disable-blink-features=AutomationControlled"],
        )
        for label, url in targets:
            results[label] = explore_site(ctx, label, url)
        ctx.close()

    out_path = OUT_DIR / "jpmm_gs_explore.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()

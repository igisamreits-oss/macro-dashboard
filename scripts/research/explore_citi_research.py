"""
Citi Research landing page 탐색 — RSCH_LANDING_PAGE API 호출 파악.

목표: 애널리스트 리포트 리스트를 반환하는 API endpoint를 찾기.
그게 발견되면 Playwright 없이도 직접 호출 가능.
"""
from __future__ import annotations

import io
import json
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


def main() -> None:
    captured: list[dict] = []

    def on_response(response):
        url = response.url
        ct = response.headers.get("content-type", "")
        method = response.request.method
        # JSON 응답 + 비-cookieconsent + 비-tracking 만
        if "json" not in ct.lower():
            return
        skip = ["cookieconsent", "go-mpulse", "glassbox", "onetrust", "epfdigitaltracking", "checkMultiple"]
        if any(s in url for s in skip):
            return
        body = ""
        try:
            body = response.text()[:2000]
        except Exception:
            pass
        post_data = None
        try:
            post_data = response.request.post_data
            if post_data and len(post_data) > 500:
                post_data = post_data[:500] + "..."
        except Exception:
            pass
        captured.append({
            "url": url,
            "method": method,
            "status": response.status,
            "post_data": post_data,
            "body_preview": body[:1500],
        })

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=["--profile-directory=Default", "--disable-blink-features=AutomationControlled"],
        )
        page = ctx.new_page()
        page.on("response", on_response)

        target = "https://www.citivelocity.com/cv2/go/RSCH_LANDING_PAGE"
        print(f"[citi-rsch] Opening {target}")
        page.goto(target, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_load_state("networkidle", timeout=45000)
        except Exception:
            pass
        time.sleep(20)

        info = {
            "final_url": page.url,
            "title": page.title(),
            "frame_count": len(page.frames),
            "frame_urls": [f.url for f in page.frames][:15],
            "body_preview": (page.evaluate("() => document.body && document.body.innerText || ''") or "")[:2000],
        }

        # 모든 iframe의 컨텐츠도 캡처
        frames_content = []
        for i, f in enumerate(page.frames):
            if not f.url or f.url == "about:blank":
                continue
            try:
                txt = f.evaluate("() => document.body && document.body.innerText || ''")
                frames_content.append({
                    "url": f.url,
                    "text_preview": (txt or "")[:1000],
                })
            except Exception as e:
                frames_content.append({"url": f.url, "error": str(e)[:100]})
        info["frames_content"] = frames_content

        # 페이지 link
        links = []
        for a in page.locator("a[href]").all()[:200]:
            try:
                href = a.get_attribute("href") or ""
                txt = (a.inner_text() or "").strip()[:120]
                if href and txt and not href.startswith("#") and "javascript:" not in href:
                    links.append({"text": txt, "href": href})
            except Exception:
                pass
        info["links"] = links[:80]

        (OUT_DIR / "citi_research.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT_DIR / "citi_research.png"), full_page=True)

        info["api_responses"] = captured

        out_path = OUT_DIR / "citi_research_explore.json"
        out_path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")

        print(f"  URL: {info['final_url']}")
        print(f"  Title: {info['title']}")
        print(f"  Frames: {info['frame_count']}")
        print(f"  Links: {len(links)}")
        print(f"  API JSON responses (non-tracking): {len(captured)}")
        print(f"  Saved: {out_path.name}")

        ctx.close()


if __name__ == "__main__":
    main()

"""
Citi Velocity 탐색 — 페이지 구조 + 네트워크 요청 가로채기.

JPMM처럼 SPA일 가능성 있어서, 페이지 HTML 외에 XHR/fetch 요청도 모두 기록.
JSON API endpoint 찾으면 그걸 직접 호출하는 게 가장 robust한 길.
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
    captured_requests: list[dict] = []

    def on_response(response):
        url = response.url
        ct = response.headers.get("content-type", "")
        # API/JSON 응답만 관심
        if "json" in ct.lower() or "/api/" in url or "research" in url.lower() or "search" in url.lower():
            captured_requests.append({
                "url": url,
                "method": response.request.method,
                "status": response.status,
                "content_type": ct[:60],
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

        print("[citi] Opening https://www.citivelocity.com/ ...")
        page.goto("https://www.citivelocity.com/", wait_until="domcontentloaded", timeout=60000)

        # SPA 충분히 렌더링
        try:
            page.wait_for_load_state("networkidle", timeout=45000)
        except Exception:
            pass
        time.sleep(15)

        info = {
            "final_url": page.url,
            "title": page.title(),
            "h1": [t for t in page.locator("h1").all_text_contents() if t.strip()][:10],
            "h2": [t for t in page.locator("h2").all_text_contents() if t.strip()][:15],
            "h3": [t for t in page.locator("h3").all_text_contents() if t.strip()][:15],
            "frame_count": len(page.frames),
            "frame_urls": [f.url for f in page.frames][:10],
            "shadow_hosts": page.evaluate("""() => {
                const hosts = [];
                document.querySelectorAll('*').forEach(el => {
                    if (el.shadowRoot) hosts.push(el.tagName + (el.id ? '#'+el.id : ''));
                });
                return hosts.slice(0, 20);
            }"""),
        }

        body = page.evaluate("() => document.body && document.body.innerText || ''")
        info["body_preview"] = body[:1500]

        # 상위 50개 의미있는 링크
        links = []
        for a in page.locator("a[href]").all()[:120]:
            try:
                href = a.get_attribute("href") or ""
                txt = (a.inner_text() or "").strip()[:100]
                if href and txt and not href.startswith("#") and "javascript:" not in href:
                    links.append({"text": txt, "href": href})
            except Exception:
                pass
        info["links"] = links[:50]

        # 전체 HTML 저장 (분석용)
        (OUT_DIR / "citi_home.html").write_text(page.content(), encoding="utf-8")
        page.screenshot(path=str(OUT_DIR / "citi_home.png"), full_page=True)

        info["captured_requests"] = captured_requests[:80]

        out_path = OUT_DIR / "citi_explore.json"
        out_path.write_text(json.dumps(info, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[citi] URL: {info['final_url']}")
        print(f"[citi] Title: {info['title']}")
        print(f"[citi] Frames: {info['frame_count']}")
        print(f"[citi] Shadow DOM hosts: {len(info['shadow_hosts'])}")
        print(f"[citi] Links found: {len(links)}")
        print(f"[citi] Captured JSON/API responses: {len(captured_requests)}")
        print(f"[citi] Saved: {out_path.name}, citi_home.html, citi_home.png")

        ctx.close()


if __name__ == "__main__":
    main()

"""
JPMM 탐색 — 저장된 세션이 살아있는지 확인 + 페이지 구조 파악.

각 URL에 접속해서:
- 최종 URL (리다이렉트 확인)
- 페이지 타이틀
- h1/h2 텍스트
- 상위 30개 링크 (text + href)
→ research-screenshots/explore.json 으로 저장
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

URLS = [
    ("home", "https://markets.jpmorgan.com/jpmm"),
]
HEADLESS = False  # SPA + 봇감지 우회 시도


def main() -> None:
    results: dict[str, dict] = {}
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=HEADLESS,
            viewport={"width": 1400, "height": 900},
            args=["--profile-directory=Default", "--disable-blink-features=AutomationControlled"],
        )
        for name, url in URLS:
            print(f"[{name}] {url}")
            page = ctx.new_page()
            info: dict = {"input_url": url}
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                # SPA 안정화: networkidle 또는 30초 대기 중 빠른 쪽
                try:
                    page.wait_for_load_state("networkidle", timeout=30000)
                except Exception:
                    pass
                time.sleep(8)
                info["final_url"] = page.url
                info["title"] = page.title()
                info["h1"] = [t for t in page.locator("h1").all_text_contents() if t.strip()][:10]
                info["h2"] = [t for t in page.locator("h2").all_text_contents() if t.strip()][:15]
                # body 텍스트 첫 600자 (로그인 페이지 vs 콘텐츠 구분)
                body = page.evaluate("() => document.body && document.body.innerText || ''")
                info["body_preview"] = body[:600]
                info["has_login_form"] = bool(
                    page.locator("input[type='password']").count()
                )
                # 상위 30개 링크
                links = []
                for a in page.locator("a[href]").all()[:60]:
                    try:
                        href = a.get_attribute("href") or ""
                        txt = (a.inner_text() or "").strip()[:80]
                        if href and txt:
                            links.append({"text": txt, "href": href})
                    except Exception:
                        pass
                info["links_sample"] = links[:30]
                page.screenshot(path=str(OUT_DIR / f"{name}.png"), full_page=False)
            except Exception as e:
                info["error"] = str(e)[:300]
            finally:
                page.close()
            results[name] = info
            print(f"  → {info.get('final_url', '?')}  title={info.get('title','?')[:60]}")
            print(f"  → login form? {info.get('has_login_form')}")
        ctx.close()

    out_path = OUT_DIR / "explore.json"
    out_path.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nWrote {out_path}")


if __name__ == "__main__":
    main()

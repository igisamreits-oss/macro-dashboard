"""
초기 세팅 — 크롬의 로그인된 Default 프로필을 chrome-profile/로 복사.

Chrome이 Default 프로필에서 remote debugging을 거부하기 때문에 Playwright는
Default를 직접 못 씀. 따라서 1회성으로 복사본을 만들고 Playwright는 그걸 사용.
쿠키는 DPAPI(Windows 사용자 계정 단위 암호화)라 복사해도 로그인 그대로 살아있음.

세션 만료(보통 30일)되면 이 스크립트를 다시 실행해서 갱신.

Usage:
    python scripts/research/setup_session.py
"""
from __future__ import annotations

import io
import os
import shutil
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
CHROME_USER_DATA = Path(os.environ["LOCALAPPDATA"]) / "Google" / "Chrome" / "User Data"

SITES = [
    ("JPMM",          "https://markets.jpmorgan.com/jpmm"),
    ("Citi Velocity", "https://www.citivelocity.com/"),
    ("GS Marquee",    "https://marquee.gs.com/s/home"),
]


def close_chrome() -> None:
    print("[setup] Closing all Chrome instances...")
    subprocess.run(["taskkill", "/F", "/IM", "chrome.exe"], capture_output=True)
    time.sleep(2)


def sync_profile() -> None:
    """크롬 Default → chrome-profile/Default 미러 복사 (캐시 제외)."""
    PROFILE_DIR.mkdir(exist_ok=True)

    # Local State (encryption key, profile list)
    src_state = CHROME_USER_DATA / "Local State"
    if src_state.exists():
        shutil.copy2(src_state, PROFILE_DIR / "Local State")

    # Default 프로필 미러 (캐시·로그 제외)
    src = CHROME_USER_DATA / "Default"
    dst = PROFILE_DIR / "Default"
    if not src.exists():
        raise SystemExit(f"Default profile not found: {src}")

    print(f"[setup] Mirroring {src} → {dst}")
    result = subprocess.run(
        [
            "robocopy", str(src), str(dst), "/MIR",
            "/XD", "Cache", "Code Cache", "GPUCache",
                   "Service Worker", "Application Cache",
                   "DawnGraphiteCache", "DawnWebGPUCache",
            "/XF", "*.tmp", "*.log", "*.lock",
            "/R:1", "/W:1", "/NFL", "/NDL", "/NJH", "/NJS",
        ],
        capture_output=True, text=True,
    )
    # robocopy returns 0-7 for success; 8+ for failure
    if result.returncode >= 8:
        print(f"  robocopy stderr: {result.stderr[:500]}")
        raise SystemExit(f"robocopy failed with code {result.returncode}")
    print(f"  ✓ Profile copy complete (robocopy exit {result.returncode})")


def main() -> None:
    close_chrome()
    sync_profile()

    print(f"[setup] Profile dir: {PROFILE_DIR}")
    print("[setup] Launching Chrome via Playwright...\n")

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            channel="chrome",
            headless=False,
            viewport={"width": 1400, "height": 900},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--profile-directory=Default",
            ],
        )

        for name, url in SITES:
            print(f"[setup] Opening {name}: {url}")
            page = ctx.new_page()
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
            except Exception as e:
                print(f"  WARN: {name} navigation: {e}")

        print("\n[setup] ✓ 3개 사이트 열림. 로그인 상태 확인 후 브라우저 닫으세요.\n")

        try:
            while len(ctx.pages) > 0:
                ctx.pages[0].wait_for_event("close", timeout=0)
        except Exception:
            pass
        ctx.close()

    print("[setup] Done. Session 저장됨.")


if __name__ == "__main__":
    main()

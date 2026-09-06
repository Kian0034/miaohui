#!/usr/bin/env python3
"""查B币余额确认扣款"""
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=False, executable_path=EXE,
        viewport={"width": 1200, "height": 800},
        args=["--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://account.bilibili.com/site/coin", wait_until="commit", timeout=90000)
    pg.wait_for_timeout(8000)
    try:
        r = pg.evaluate("""async ()=>{
            const res = await fetch('https://account.bilibili.com/site/getCoin',{credentials:'include'});
            const j = await res.json();
            return j;
        }""")
        print(f"B币余额: {r}", flush=True)
    except Exception as e:
        print(f"err: {e}", flush=True)
    pg.screenshot(path="/Users/ff/miaohui/video/shots/coin_check.png")
    ctx.close()

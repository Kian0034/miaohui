#!/usr/bin/env python3
"""直接截图稿件管理页"""
import time
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/upload-manager/article",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)
    pg.goto("https://member.bilibili.com/platform/upload-manager/article",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)
    pg.screenshot(path="/Users/ff/miaohui/video/shots/upload_mgr.png")
    print("title:", pg.title())
    txt = pg.evaluate("()=>document.body.innerText.slice(0,600)")
    print(txt)
    ctx.close()

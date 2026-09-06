#!/usr/bin/env python3
"""必火推广：从侧边栏进入推广页，dump结构"""
import time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=False, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/home", wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)

    # 点侧边栏 必火推广
    clicked = False
    for sel in ['text=必火推广', 'a:has-text("必火推广")', '[class*="menu"]:has-text("必火推广")']:
        try:
            loc = pg.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                clicked = True
                break
        except Exception:
            continue
    print("clicked:", clicked, flush=True)
    time.sleep(10)
    print("URL:", pg.url[:90], flush=True)
    pg.screenshot(path=f"{SHOTS}/promo1.png", full_page=False)
    body = pg.evaluate("()=>document.body.innerText.slice(0,1200)")
    print(body[:800].replace("\n", "|"), flush=True)

    # 找B币相关
    coin = pg.evaluate("""()=>{
        const t = document.body.innerText;
        const ms = t.match(/B币[^\n]{0,30}/g);
        return ms;
    }""")
    print("B币文本:", coin, flush=True)
    ctx.close()

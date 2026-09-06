#!/usr/bin/env python3
"""必火推广侦察：进入创作中心推广页，dump可选稿件与B币余额"""
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

    # B币余额
    pg.goto("https://account.bilibili.com/big/self", wait_until="domcontentloaded", timeout=60000)
    time.sleep(6)
    coin = pg.evaluate("""()=>{
        const t = document.body.innerText;
        const m = t.match(/B币[^\\d]{0,20}(\\d+(?:\\.\\d+)?)/);
        return m ? m[1] : null;
    }""")
    print("B币余额:", coin, flush=True)

    # 推广中心
    for url in ["https://member.bilibili.com/platform/promotion",
                "https://member.bilibili.com/york/promotion",
                "https://member.bilibili.com/platform/tools/promotion"]:
        pg.goto(url, wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)
        cur = pg.url
        title = pg.title()
        body = pg.evaluate("()=>document.body.innerText.slice(0,700)")
        print(f"== {url} -> {cur[:80]} | {title}", flush=True)
        print(body[:400].replace("\n", "|"), flush=True)
        pg.screenshot(path=f"{SHOTS}/promo_{url[-15:].replace('/','_')}.png")
    ctx.close()

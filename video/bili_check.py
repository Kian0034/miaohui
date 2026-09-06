#!/usr/bin/env python3
"""查看稿件进度：获取BV号、审核状态、封面状态"""
import time, json, re
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/upload-manager/article",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)
    pg.screenshot(path=f"{SHOTS}/g1_manager.png")

    # API直接查稿件列表更可靠
    data = pg.evaluate("""async ()=>{
        const r = await fetch('/x/vupre/web/archive/list?pn=1&ps=10', {credentials:'include'});
        return await r.json();
    }""")
    if data.get("code") == 0:
        for arc in data["data"]["arc_audits"] or []:
            a = arc["Archive"]
            print(json.dumps({
                "bvid": a["bvid"], "title": a["title"][:40], "state": a["state"],
                "state_desc": a.get("state_desc",""), "cover": a["cover"][:60],
                "pubtime": a["pubtime"], "desc": (a["desc"] or "")[:50]
            }, ensure_ascii=False, indent=1))
    else:
        print("API:", json.dumps(data, ensure_ascii=False)[:300])
    ctx.close()

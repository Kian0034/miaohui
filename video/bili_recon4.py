#!/usr/bin/env python3
"""侦察4：对第2个file input设置文件，监控上传直到表单出现"""
import os, time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
VIDEO = "/Users/ff/miaohui/video/output/final_v1.mp4"
SHOTS = "/Users/ff/miaohui/video/shots"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/upload/video/frame",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)

    # 用可见的第二个input
    inp = pg.locator('input[type=file]:visible').first
    print("inputs visible:", pg.locator('input[type=file]:visible').count(), flush=True)
    inp.set_input_files(VIDEO)
    print("[ok] 文件已设置", flush=True)

    form = False
    for i in range(100):
        try:
            if pg.locator('input[placeholder*="标题"]').count() > 0:
                form = True
                print(f"[ok] 表单就绪 ({i*3}s)", flush=True)
                break
        except Exception:
            pass
        if i % 8 == 7:
            print(f"  ...{i*3}s", flush=True)
            pg.screenshot(path=f"{SHOTS}/r4_t{i}.png")
        time.sleep(3)

    time.sleep(6)
    pg.screenshot(path=f"{SHOTS}/r4_final.png")
    print("form:", form, "| url:", pg.url[:80], flush=True)
    ctx.close()

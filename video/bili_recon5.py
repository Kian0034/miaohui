#!/usr/bin/env python3
"""侦察5：点击继续编辑恢复草稿 + 监控网络"""
import os, time, json
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
    reqs = []
    pg.on("request", lambda r: reqs.append(f"{r.method} {r.url[:110]}") if any(
        k in r.url for k in ["upload", "preup", "upos", "archive", "videoup"]) else None)
    pg.goto("https://member.bilibili.com/platform/upload/video/frame",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)

    clicked = False
    for fr in pg.frames:
        try:
            loc = fr.locator('.tip-btn-group > div').first
            if loc.count() > 0:
                loc.click(timeout=5000)
                clicked = True
                print("[ok] 点击 继续编辑", flush=True)
                break
        except Exception as e:
            print(f"  err {str(e)[:60]}", flush=True)
    if not clicked:
        # 兜底: 找文本按钮
        try:
            t = pg.locator('text=继续编辑').first
            if t.count() > 0:
                t.click()
                clicked = True
                print("[ok] 文本方式点击 继续编辑", flush=True)
        except Exception as e:
            print(f"  兜底err: {str(e)[:60]}", flush=True)

    time.sleep(10)
    form = False
    for i in range(40):
        try:
            if pg.locator('input[placeholder*="标题"]').count() > 0:
                form = True
                print(f"[ok] 表单就绪 ({i*3}s)", flush=True)
                break
        except Exception:
            pass
        time.sleep(3)
    time.sleep(5)
    pg.screenshot(path=f"{SHOTS}/r5_resume.png")
    print("form:", form, flush=True)
    print("--- 网络请求 ---", flush=True)
    for r in reqs[-25:]:
        print(r, flush=True)
    ctx.close()

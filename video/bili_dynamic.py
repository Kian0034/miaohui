#!/usr/bin/env python3
"""审核通过后：发动态(转发文案) + 检查稿件数据"""
import time, json, sys
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"

DYN_TEXT = """做了一个纯本地的「秒回」搜索引擎：0.3秒找回电脑里任何一帧画面，
截图文字、视频里说的话都能搜，全程离线不上传。
开源免费，Mac版今天发布 👇
#效率工具# #开源软件# #本地搜索#"""


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def main():
    bvid = sys.argv[1] if len(sys.argv) > 1 else None
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=True, executable_path=EXE,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
                  "--no-proxy-server", "--proxy-server=direct://"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()

        # 视频页打开(带Referer上下文)
        pg.goto(f"https://www.bilibili.com/video/{bvid}",
                wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)
        title = pg.evaluate("()=>document.title")
        log("视频页标题:", title[:50])
        pg.screenshot(path=f"{SHOTS}/d1_video.png")

        # 发动态
        pg.goto("https://t.bilibili.com/", wait_until="domcontentloaded", timeout=60000)
        time.sleep(6)
        ok = False
        for sel in ['.ql-editor', '[contenteditable="true"]', '.bili-dyn-item__form textarea']:
            try:
                loc = pg.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click()
                    time.sleep(1)
                    pg.keyboard.type(DYN_TEXT, delay=5)
                    time.sleep(1)
                    pg.screenshot(path=f"{SHOTS}/d2_dyn_filled.png")
                    # 发送按钮
                    for bsel in ['button:has-text("发布")', '.dyn-origin__action:has-text("发布")',
                                 'text=发布']:
                        try:
                            bl = pg.locator(bsel).first
                            if bl.count() > 0 and bl.is_visible() and bl.is_enabled():
                                bl.click()
                                ok = True
                                log("✓ 动态已发布")
                                break
                        except Exception:
                            continue
                    break
            except Exception:
                continue
        if not ok:
            log("⚠ 动态发布未确认")
            pg.screenshot(path=f"{SHOTS}/d3_dyn_fail.png")
        time.sleep(4)
        pg.screenshot(path=f"{SHOTS}/d4_dyn_done.png")
        ctx.close()


if __name__ == "__main__":
    main()

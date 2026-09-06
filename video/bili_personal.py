#!/usr/bin/env python3
"""个性化配置：投票弹幕(前10秒) + 一键三连弹幕(结尾)"""
import time, json, sys
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"
BV = "BVHgBzVhbcto"
DUR = 101  # 视频秒数

VOTE_Q = "你电脑里最难找的是什么？"
VOTE_OPTS = ["某张截图", "某个视频里的一帧", "文件名忘了的文档"]


def log(*a):
    line = f"[{time.strftime('%H:%M:%S')}] " + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open("/Users/ff/miaohui/video/personal.log", "a") as f:
        f.write(line + "\n")


def shot(pg, name):
    try:
        pg.screenshot(path=f"{SHOTS}/{name}.png", timeout=8000)
    except Exception:
        pass


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, executable_path=EXE,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
                  "--no-proxy-server", "--proxy-server=direct://"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.set_default_timeout(20000)

        pg.goto("https://member.bilibili.com/platform/upload-manager/article",
                wait_until="domcontentloaded", timeout=60000)
        time.sleep(9)
        shot(pg, "p1_list")

        # 找到目标稿件行的三点菜单(更多操作)
        opened = False
        row = pg.locator('div.archive-item, .content-row, [class*="archive"]').filter(has_text="秒回").first
        try:
            if row.count() > 0:
                more = row.locator('[class*="more"], [class*="dots"], .__dropdown, [class*="menu"]').first
                if more.count() > 0:
                    more.hover()
                    time.sleep(1.5)
                    shot(pg, "p2_hover")
                    opened = True
        except Exception as e:
            log("hover err:", str(e)[:80])

        # 兜底: 直接找页面上所有"个性化配置"文本
        target = None
        for sel in ['text=个性化配置', '[class*="dropdown"] :text("个性化配置")']:
            try:
                loc = pg.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    target = loc
                    break
            except Exception:
                pass
        if target:
            target.click()
            log("✓ 进入个性化配置")
            time.sleep(6)
        else:
            # 直接猜测URL
            pg.goto(f"https://member.bilibili.com/platform/upload-manager/individualize?bvid={BV}",
                    wait_until="domcontentloaded", timeout=60000)
            time.sleep(8)
            log("尝试直接URL进入个性化配置")
        shot(pg, "p3_personal")

        body = pg.evaluate("()=>document.body.innerText.slice(0,600)")
        log("页面文本:", body[:200].replace("\n", "|"))
        ctx.close()


if __name__ == "__main__":
    main()

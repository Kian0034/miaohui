#!/usr/bin/env python3
"""必火推广v4：找套餐/预算选项并设置为239元"""
import time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"


def shot(pg, name):
    try:
        pg.screenshot(path=f"{SHOTS}/{name}.png", timeout=8000)
        print(f"[shot] {name}", flush=True)
    except Exception as e:
        print(f"[shot err] {name}: {str(e)[:60]}", flush=True)


def find_app_frame(pg):
    for f in pg.frames:
        try:
            if "你要推广的稿件" in (f.evaluate("()=>document.body.innerText.slice(0,3000)") or ""):
                return f
        except Exception:
            continue
    return None


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=False, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.set_default_timeout(12000)

    pg.goto("https://member.bilibili.com/platform/growingUp/fly",
            wait_until="domcontentloaded", timeout=60000)
    fr = None
    for i in range(15):
        fr = find_app_frame(pg)
        if fr:
            break
        time.sleep(2)
    print("frame ok", flush=True)

    # 关弹窗
    for sel in ['text=下次再说', '[class*="close"]']:
        try:
            loc = fr.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                time.sleep(1.5)
                break
        except Exception:
            continue

    # 互动量 + 选卡片
    try:
        fr.locator('text=互动量').first.click()
        time.sleep(2)
    except Exception:
        pass
    try:
        card = fr.locator('[class*="card"]:has-text("秒回")').first
        box = card.bounding_box()
        if box:
            pg.mouse.click(box["x"] + 60, box["y"] + box["height"] / 2)
            time.sleep(2)
    except Exception:
        pass
    shot(pg, "w1_selected")

    # 点击底部"实付"金额区域（可能是套餐选择下拉）
    clicked = False
    for sel in ['text=选择的套餐', 'text=实付', '[class*="package"]', '[class*="combo"]',
                '[class*="amount"]', '[class*="price"]']:
        try:
            loc = fr.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                clicked = True
                print(f"✓ 点击了 {sel}", flush=True)
                time.sleep(2)
                break
        except Exception:
            continue
    shot(pg, "w2_pkg_click")

    # dump弹出的选项
    info = fr.evaluate("""()=>{
        const out = {lines: [], radios: []};
        document.body.innerText.split('\\n').forEach(l=>{
            const t = l.trim();
            if (t && t.length < 60 && /套餐|元|天|¥|预算|自定义|转化|播放/.test(t)) out.lines.push(t);
        });
        document.querySelectorAll('[class*="option"],[class*="item"],[class*="package"],[class*="combo"],li').forEach(e=>{
            const r = e.getBoundingClientRect();
            const t = (e.innerText||'').trim().replace(/\\n/g,' ');
            if (r.width > 0 && t && t.length < 40 && /元|¥|天/.test(t)) out.radios.push({t, cls:(e.className||'').toString().slice(0,40), y: Math.round(r.y)});
        });
        return {lines: out.lines.slice(0,30), opts: out.radios.slice(0,20)};
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=1), flush=True)
    shot(pg, "w3_pkg_dump")
    ctx.close()

#!/usr/bin/env python3
"""必火推广投放：互动量+锁定人群+B币支付（分步截图）"""
import os, time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"
PAY = os.environ.get("PAY", "0") == "1"  # PAY=1 才最终点支付


def shot(pg, name):
    try:
        pg.screenshot(path=f"{SHOTS}/{name}.png", timeout=8000)
        print(f"[shot] {name}", flush=True)
    except Exception as e:
        print(f"[shot err] {name}: {str(e)[:60]}", flush=True)


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=False, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.set_default_timeout(15000)

    pg.goto("https://member.bilibili.com/platform/home", wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)
    # 侧边栏进必火推广
    for sel in ['text=必火推广']:
        try:
            loc = pg.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                break
        except Exception:
            continue
    time.sleep(9)

    # 关弹窗
    for sel in ['text=下次再说', '[class*="close"]']:
        try:
            loc = pg.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                print("弹窗已关", flush=True)
                time.sleep(1)
                break
        except Exception:
            pass
    shot(pg, "pay1_page")

    # 选择秒回稿件卡片（含"秒回"文本的卡片）
    card = None
    for fr in pg.frames:
        try:
            loc = fr.locator('[class*="card"], [class*="video-item"], [class*="archive"]').filter(has_text="秒回").first
            if loc.count() > 0:
                card = loc
                print("找到秒回卡片 (frame:", fr.url[:40], ")", flush=True)
                break
        except Exception:
            pass
    if card:
        try:
            card.click()
            time.sleep(2)
            print("✓ 已选秒回稿件", flush=True)
        except Exception as e:
            print("卡片点击:", str(e)[:80], flush=True)
    shot(pg, "pay2_card")

    # 提升目标: 互动量
    for sel in ['text=互动量']:
        try:
            loc = pg.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                print("✓ 选了互动量", flush=True)
                time.sleep(2)
                break
        except Exception:
            continue
    shot(pg, "pay3_goal")

    # dump页面上的金额/时长/人群控件
    info = pg.evaluate("""()=>{
        const out = {texts: [], inputs: []};
        document.querySelectorAll('input[type=text],input[type=number],input:not([type])').forEach(e=>{
            const r=e.getBoundingClientRect();
            if(r.width>0) out.inputs.push({ph:e.placeholder||'', val:e.value||'', cls:(e.className||'').toString().slice(0,40)});
        });
        const t = document.body.innerText;
        // 抓取含关键词的行
        t.split('\\n').forEach(line=>{
            if(/预算|金额|元|天|时长|人群|定向|地域|年龄|支付|B币|预计/.test(line) && line.trim().length<60) out.texts.push(line.trim());
        });
        return {inputs: out.inputs.slice(0,15), lines: out.texts.slice(0,40)};
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=1), flush=True)
    shot(pg, "pay4_dump")
    ctx.close()

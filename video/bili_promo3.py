#!/usr/bin/env python3
"""必火推广v2：在cm.bilibili.com iframe内操作"""
import os, time, json
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


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=False, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.set_default_timeout(12000)

    pg.goto("https://member.bilibili.com/platform/home", wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)
    pg.locator('text=必火推广').first.click()
    time.sleep(9)

    # 进入iframe
    fr = None
    for attempt in range(6):
        for f in pg.frames:
            if "fly-pc" in (f.url or ""):
                fr = f
                break
        if fr:
            break
        print(f"  等待iframe... ({attempt}) frames:", [f.url[:50] for f in pg.frames], flush=True)
        time.sleep(4)
    if not fr:
        print("!! 没找到fly-pc iframe", flush=True)
        ctx.close()
        exit(1)
    print("iframe:", fr.url[:60], flush=True)

    # 1. 关弹窗
    for sel in ['text=下次再说', 'text=以后再说', '[class*="close"]']:
        try:
            loc = fr.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                print("✓ 弹窗已关", flush=True)
                time.sleep(1.5)
                break
        except Exception:
            continue
    shot(pg, "q1_dismissed")

    # 2. 选互动量
    try:
        fr.locator('text=互动量').first.click()
        print("✓ 选了互动量", flush=True)
        time.sleep(2)
    except Exception as e:
        print("互动量:", str(e)[:70], flush=True)
    shot(pg, "q2_inter")

    # 3. 选秒回稿件卡片
    try:
        card = fr.locator('[class*="card"],[class*="video"],[class*="archive"],li,div').filter(
            has_text="秒回").first
        # 尝试点击卡片本身
        card.click(timeout=6000)
        print("✓ 已选秒回稿件", flush=True)
        time.sleep(2)
    except Exception as e:
        print("卡片:", str(e)[:70], flush=True)
        # 兜底: 点封面图区域坐标
        try:
            box = fr.locator('text=19').first.bounding_box()
            if box:
                pg.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
                print("✓ 坐标点击卡片", flush=True)
                time.sleep(2)
        except Exception:
            pass
    shot(pg, "q3_card")

    # 4. dump预算/时长/人群控件
    info = fr.evaluate("""()=>{
        const out = {lines: [], inputs: [], buttons: []};
        document.body.innerText.split('\\n').forEach(l=>{
            const t = l.trim();
            if (t && t.length < 50 && /预算|金额|元|天|时长|人群|定向|地域|年龄|兴趣|支付|B币|预计|投放/.test(t)) out.lines.push(t);
        });
        document.querySelectorAll('input').forEach(e=>{
            const r = e.getBoundingClientRect();
            if (r.width > 0) out.inputs.push({type: e.type, ph: e.placeholder||'', val: (e.value||'').slice(0,20), cls:(e.className||'').toString().slice(0,40)});
        });
        document.querySelectorAll('button, [class*="btn"]').forEach(e=>{
            const r = e.getBoundingClientRect();
            const t = (e.innerText||'').trim();
            if (r.width > 0 && t && t.length < 15) out.buttons.push(t);
        });
        return out;
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=1), flush=True)
    shot(pg, "q4_dump")
    ctx.close()

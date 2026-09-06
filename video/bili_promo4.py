#!/usr/bin/env python3
"""必火推广v3：按内容定位frame，关弹窗→互动量→选稿件→dump预算控件"""
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
            print(f"✓ 找到应用frame ({i*2}s)", flush=True)
            break
        time.sleep(2)
    if not fr:
        print("frames:", [f.url[:60] for f in pg.frames], flush=True)
        shot(pg, "q0_noframe")
        ctx.close()
        exit(1)

    # 1. 关弹窗（在app frame内）
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
    shot(pg, "q1_ready")

    # 2. 选互动量
    try:
        fr.locator('text=互动量').first.click()
        print("✓ 选了互动量", flush=True)
        time.sleep(2)
    except Exception as e:
        print("互动量:", str(e)[:70], flush=True)
    shot(pg, "q2_inter")

    # 3. 选秒回稿件（点其封面区域——找含19播放的卡片）
    ok = False
    for sel in ['[class*="card"]:has-text("秒回")', '[class*="item"]:has-text("秒回")',
                'div:has-text("秒回」")']:
        try:
            loc = fr.locator(sel).first
            if loc.count() > 0:
                box = loc.bounding_box()
                if box:
                    # 点卡片左侧封面位置（避开可能的悬浮按钮）
                    pg.mouse.click(box["x"] + 60, box["y"] + box["height"] / 2)
                    ok = True
                    print(f"✓ 点了卡片 ({sel[:30]})", flush=True)
                    time.sleep(2)
                    break
        except Exception:
            continue
    if not ok:
        # 兜底：点封面上"19"附近的坐标
        try:
            b19 = fr.locator('text=19').first.bounding_box()
            if b19:
                pg.mouse.click(b19["x"] + b19["width"] / 2, b19["y"] + b19["height"] / 2)
                print("✓ 坐标点击(19)", flush=True)
                time.sleep(2)
        except Exception:
            pass
    shot(pg, "q3_card")

    # 4. dump控件
    info = fr.evaluate("""()=>{
        const out = {lines: [], inputs: [], buttons: []};
        document.body.innerText.split('\\n').forEach(l=>{
            const t = l.trim();
            if (t && t.length < 50 && /预算|金额|元|天|时长|人群|定向|地域|年龄|兴趣|支付|B币|预计|投放|选择/.test(t)) out.lines.push(t);
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

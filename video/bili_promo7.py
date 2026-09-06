#!/usr/bin/env python3
"""必火推广v6：切换至自定义→填239→立即支付"""
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


def dump_state(sc, tag):
    try:
        info = sc.evaluate("""()=>{
            const lines=[];
            document.body.innerText.split('\\n').forEach(l=>{
                const t=l.trim();
                if(t && t.length<50 && /实付|支付|预算|自定义|投入|预计/.test(t)) lines.push(t);
            });
            const inputs=[];
            document.querySelectorAll('input').forEach(e=>{
                const r=e.getBoundingClientRect();
                if(r.width>0) inputs.push({type:e.type,val:e.value,ph:e.placeholder||'',x:Math.round(r.x),y:Math.round(r.y)});
            });
            return {lines:lines.slice(0,20),inputs:inputs.slice(0,10)};
        }""")
        print(f"[dump:{tag}] {json.dumps(info, ensure_ascii=False)}", flush=True)
        return info
    except Exception as e:
        print(f"[dump err:{tag}] {str(e)[:60]}", flush=True)
        return {"inputs": []}


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

    # 互动量tab
    try:
        fr.locator('text=互动量').first.click()
        time.sleep(2)
    except Exception:
        pass

    # 点击右上角"切换至自定义"
    sw = False
    for sel in ['text=切换至自定义', 'span:has-text("切换至自定义")']:
        try:
            loc = fr.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                sw = True
                print(f"✓ 点击了 {sel}", flush=True)
                time.sleep(2.5)
                break
        except Exception:
            continue
    if not sw:
        print("!! 切换至自定义失败", flush=True)
    shot(pg, "c1_switched")
    dump_state(fr, "after_switch")

    # 填239到自定义预算输入框
    filled = False
    for attempt in range(3):
        els = fr.locator("input:visible")
        n = els.count()
        print(f"attempt{attempt}: {n} visible inputs", flush=True)
        for i in range(n):
            try:
                el = els.nth(i)
                ph = el.get_attribute("placeholder") or ""
                tp = el.get_attribute("type") or ""
                print(f"  input{i}: type={tp} ph={ph}", flush=True)
                if tp in ("number", "text", "tel") or any(k in ph for k in ["金额", "预算", "输入", "自定义"]):
                    el.click()
                    time.sleep(0.5)
                    el.fill("239")
                    filled = True
                    print(f"✓ 填入239 (type={tp} ph={ph})", flush=True)
                    break
            except Exception:
                continue
        if filled:
            break
        time.sleep(2)
    shot(pg, "c2_filled")

    if filled:
        pg.keyboard.press("Enter")
        time.sleep(2.5)
    dump_state(fr, "after_fill")
    shot(pg, "c3_paybar")

    paybar = fr.evaluate("""()=>{
        const t=document.body.innerText;
        const m=t.match(/实付[^\\n]{0,20}/);
        return m?m[0]:'';
    }""")
    print(f"paybar: {paybar}", flush=True)

    if "239" in (paybar or ""):
        paid = False
        for sel in ['button:has-text("立即支付")', 'text=立即支付']:
            try:
                loc = fr.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click()
                    paid = True
                    print(f"✓ 点击了 {sel}", flush=True)
                    break
            except Exception:
                continue
        time.sleep(4)
        shot(pg, "c4_paypanel")
        dump_state(fr, "pay_frame")
        dump_state(pg.main_frame, "pay_main")

        # 优先B币支付
        for scope in [fr, pg]:
            try:
                for sel in ['text=B币支付', 'text=B币余额', '[class*="bcoin"]']:
                    loc = scope.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click()
                        print(f"✓ 选了B币支付", flush=True)
                        time.sleep(2)
                        break
            except Exception:
                continue
        shot(pg, "c5_bcoin")

        for scope in [fr, pg]:
            for sel in ['button:has-text("确认支付")', 'text=确认支付',
                        'button:has-text("立即支付")', 'button:has-text("确定")']:
                try:
                    loc = scope.locator(sel).first
                    if loc.count() > 0 and loc.is_visible() and loc.is_enabled():
                        loc.click()
                        print(f"✓ 点击了 {sel}", flush=True)
                        time.sleep(4)
                        break
                except Exception:
                    continue
        shot(pg, "c6_final")
        dump_state(fr, "final")
    else:
        print("!! 实付金额不是239，中止支付", flush=True)

    time.sleep(20)
    ctx.close()

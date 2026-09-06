#!/usr/bin/env python3
"""必火推广v5：选自定义套餐填239，立即支付（优先B币）"""
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


def dump_pay(fr, tag):
    info = fr.evaluate("""()=>{
        const lines=[];
        document.body.innerText.split('\\n').forEach(l=>{
            const t=l.trim();
            if(t && t.length<50 && /实付|支付|B币|余额|扫码|支付宝|微信|确认|价格|预算|元/.test(t)) lines.push(t);
        });
        const btns=[];
        document.querySelectorAll('button,[class*="btn"],[class*="pay"],a').forEach(e=>{
            const r=e.getBoundingClientRect();
            const t=(e.innerText||'').trim().replace(/\\n/g,' ');
            if(r.width>0&&r.height>0&&t&&t.length<30&&/支付|确认|立即/.test(t)) btns.push(t);
        });
        const inputs=[];
        document.querySelectorAll('input').forEach(e=>{
            const r=e.getBoundingClientRect();
            if(r.width>0) inputs.push({type:e.type,val:e.value,ph:e.placeholder||''});
        });
        return {lines:lines.slice(0,25),btns:btns.slice(0,10),inputs:inputs.slice(0,10)};
    }""")
    print(f"[dump:{tag}] {json.dumps(info, ensure_ascii=False)}", flush=True)
    return info


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

    # 点击"自定义"套餐卡片
    clicked = False
    for sel in ['text=自定义', '[class*="card"]:has-text("自定义")']:
        try:
            loc = fr.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                clicked = True
                print(f"✓ 点击了 {sel}", flush=True)
                time.sleep(2.5)
                break
        except Exception:
            continue
    if not clicked:
        print("!! 自定义点击失败", flush=True)
    shot(pg, "p1_custom")

    # 找自定义金额输入框并填239
    filled = False
    for attempt in range(3):
        inputs = fr.locator("input:visible")
        n = inputs.count()
        print(f"attempt{attempt}: {n} visible inputs", flush=True)
        for i in range(n):
            try:
                el = inputs.nth(i)
                ph = el.get_attribute("placeholder") or ""
                tp = el.get_attribute("type") or ""
                print(f"  input{i}: type={tp} ph={ph}", flush=True)
                if ph and any(k in ph for k in ["金额", "预算", "自定义", "输入"]):
                    el.click()
                    time.sleep(0.5)
                    el.fill("239")
                    filled = True
                    print(f"✓ 填入239 (ph={ph})", flush=True)
                    break
            except Exception:
                continue
        if filled:
            break
        # 兜底：点输入框附近再试
        try:
            fr.locator('input[type="number"]').first.click(timeout=3000)
            fr.locator('input[type="number"]').first.fill("239")
            filled = True
            print("✓ 填入239 (number)", flush=True)
            break
        except Exception:
            time.sleep(2)
    if not filled:
        # 最后兜底：点所有可见输入框
        try:
            els = fr.locator("input:visible")
            for i in range(els.count()):
                try:
                    els.nth(i).click()
                    els.nth(i).fill("239")
                    filled = True
                    print(f"✓ 填入239 (input{i})", flush=True)
                    break
                except Exception:
                    continue
        except Exception:
            pass
    shot(pg, "p2_filled")

    # 回车让数值生效
    try:
        pg.keyboard.press("Enter")
        time.sleep(2)
    except Exception:
        pass
    info = dump_pay(fr, "after_fill")
    shot(pg, "p3_paybar")

    # 校验实付金额为239再支付
    paybar = fr.evaluate("""()=>{
        const t=document.body.innerText;
        const m=t.match(/实付[^\\n]{0,20}/);
        return m?m[0]:'';
    }""")
    print(f"paybar: {paybar}", flush=True)

    if "239" in (paybar or "") or any("239" in (i.get("val") or "") for i in info.get("inputs", [])):
        # 点击立即支付
        paid = False
        for sel in ['button:has-text("立即支付")', 'text=立即支付', 'button:has-text("支付")']:
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
        shot(pg, "p4_paypanel")

        # 支付弹窗可能在主页面而非frame，都dump一遍
        try:
            dump_pay(fr, "in_frame")
        except Exception:
            pass
        info2 = None
        try:
            info2 = dump_pay(pg.main_frame, "main_frame")
        except Exception:
            pass

        # 优先B币支付
        for scope in [fr, pg]:
            try:
                for sel in ['text=B币支付', 'text=B币余额', '[class*="bcoin"]', 'text=币支付']:
                    loc = scope.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click()
                        print(f"✓ 选了B币支付 {sel}", flush=True)
                        time.sleep(2)
                        break
            except Exception:
                continue
        shot(pg, "p5_bcoin")

        # 确认支付
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
        shot(pg, "p6_final")
        try:
            dump_pay(fr, "final")
        except Exception:
            pass
    else:
        print("!! 实付金额不是239，中止支付", flush=True)
        try:
            dump_pay(fr, "no239")
        except Exception:
            pass

    # 保持浏览器30秒便于观察
    time.sleep(30)
    ctx.close()

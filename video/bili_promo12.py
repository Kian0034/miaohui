#!/usr/bin/env python3
"""必火推广v11：cus弹窗填239→确定→立即支付→B币支付"""
import time, json, re
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


def amounts(sc):
    try:
        t = sc.evaluate("()=>document.body.innerText")
        return [float(x) for x in re.findall(r"[¥￥]\s*([0-9]+(?:\.[0-9]{1,2})?)", t or "")]
    except Exception:
        return []


def paybar(sc):
    try:
        t = sc.evaluate("()=>document.body.innerText")
        m = re.search(r"实付款?\s*[¥￥]?[0-9.]*", t or "")
        return m.group(0) if m else ""
    except Exception:
        return ""


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

    for sel in ['text=下次再说', '[class*="close"]']:
        try:
            loc = fr.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                time.sleep(1.5)
                break
        except Exception:
            continue

    try:
        fr.locator('text=互动量').first.click()
        time.sleep(2)
    except Exception:
        pass

    # 1) JS点击 span.cus 弹出金额弹窗
    fr.evaluate("""()=>{const c=document.querySelector('span.cus');if(c){c.scrollIntoView({block:'center'});c.click();}}""")
    print("✓ 点击自定义勾选", flush=True)
    time.sleep(2.5)
    shot(pg, "h1_dialog")

    # 2) 弹窗输入框填239（逐键输入）
    inp = fr.locator('input[placeholder*="投放金额"]').first
    if inp.count() == 0:
        inp = fr.locator('input:visible').first
    inp.click()
    time.sleep(0.8)
    pg.keyboard.type("239", delay=60)
    time.sleep(1.5)
    val = inp.input_value()
    print(f"输入框值: {val}", flush=True)
    shot(pg, "h2_typed")

    # 3) 点弹窗"确定"
    ok_clicked = False
    locs = fr.locator('button:has-text("确定")')
    for i in range(locs.count()):
        try:
            if locs.nth(i).is_visible():
                locs.nth(i).click()
                ok_clicked = True
                print(f"✓ 弹窗确定 #{i}", flush=True)
                break
        except Exception:
            continue
    if not ok_clicked:
        fr.evaluate("""()=>{const bs=[...document.querySelectorAll('button')].filter(b=>(b.innerText||'').trim()==='确定'&&b.offsetParent);if(bs.length)bs[0].click();}""")
        print("✓ JS点确定", flush=True)
    time.sleep(3)
    shot(pg, "h3_confirmed")

    pb = paybar(fr)
    am = amounts(fr)
    print(f"确定后: paybar={pb} amts={am}", flush=True)

    # 4) 校验239后点底部立即支付
    if "239" in pb or any(abs(a - 239) < 0.01 for a in am):
        pg.mouse.click(1218, 859)
        print("✓ 坐标点底部立即支付", flush=True)
        time.sleep(4)
        shot(pg, "h4_paypanel")
        am2 = amounts(fr)
        print(f"支付弹窗金额: {am2}", flush=True)

        # 5) 选B币支付
        try:
            loc = fr.locator('text=B币支付').first
            if loc.count() > 0 and loc.is_visible():
                loc.click()
                print("✓ 选B币支付", flush=True)
                time.sleep(2)
        except Exception:
            pass
        shot(pg, "h5_bcoin")

        # 6) 弹窗金额=239 → 立即支付
        am3 = amounts(fr)
        pb3 = paybar(fr)
        print(f"确认: amts={am3} paybar={pb3}", flush=True)
        if any(abs(a - 239) < 0.01 for a in am3) or "239" in pb3:
            done = False
            locs = fr.locator('button:has-text("立即支付")')
            for i in range(locs.count()):
                try:
                    if locs.nth(i).is_visible():
                        locs.nth(i).click()
                        done = True
                        print(f"✓ 支付弹窗立即支付 #{i}", flush=True)
                        time.sleep(6)
                        break
                except Exception:
                    continue
            shot(pg, "h6_after_pay")
            t = fr.evaluate("()=>document.body.innerText")
            for kw in ["支付成功", "推广成功", "已支付"]:
                if kw in t:
                    print(f"✓✓✓ {kw}!", flush=True)
                    break
            # 收尾弹窗
            for sel in ['button:has-text("我知道了")', 'button:has-text("确定")', 'button:has-text("完成")', 'button:has-text("查看订单")']:
                try:
                    loc = fr.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click()
                        print(f"✓ 收尾 {sel}", flush=True)
                        time.sleep(3)
                        break
                except Exception:
                    continue
            shot(pg, "h7_final")
            t = fr.evaluate("()=>document.body.innerText")
            m = re.search(r"(支付成功|推广成功|投放成功|订单[^\\n]{0,30})", t or "")
            print(f"最终状态: {m.group(0) if m else t[:200]}", flush=True)
        else:
            print(f"!! 弹窗金额非239: {am3}", flush=True)
            shot(pg, "h_abort2")
            try:
                fr.locator('button:has-text("取消")').first.click()
            except Exception:
                pass
    else:
        print(f"!! 实付非239: paybar={pb} amts={am}", flush=True)
        shot(pg, "h_abort")

    time.sleep(12)
    ctx.close()

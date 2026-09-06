#!/usr/bin/env python3
"""必火推广v10：多策略点击自定义卡片→填239→B币支付"""
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


def state(fr):
    try:
        return fr.evaluate("""()=>{
            const vis=[...document.querySelectorAll('input,[contenteditable="true"]')].filter(e=>{
                const r=e.getBoundingClientRect();return r.width>0&&r.height>0;
            }).map(e=>({tag:e.tagName,type:e.type||'',ph:e.placeholder||''}));
            let num='';
            document.querySelectorAll('.num,.din,[class*="num"]').forEach(e=>{
                if((e.innerText||'').trim()==='-----') num=(e.className||'').toString().slice(0,30);
            });
            const t=document.body.innerText;
            const hasDialog=t.includes('确认订单并支付');
            const m=t.match(/实付[^\\n]{0,15}/);
            return {vis, num, hasDialog, paybar:m?m[0]:''};
        }""")
    except Exception as e:
        print(f"state err: {str(e)[:60]}", flush=True)
        return {"vis": [], "num": "", "hasDialog": False, "paybar": ""}


def amounts(fr):
    try:
        t = fr.evaluate("()=>document.body.innerText")
        return [float(x) for x in re.findall(r"[¥￥]\s*([0-9]+(?:\.[0-9]{1,2})?)", t or "")]
    except Exception:
        return []


def js_click(fr, js, name):
    try:
        r = fr.evaluate(js)
        if r:
            print(f"✓ JS点击 {name}", flush=True)
            time.sleep(2.5)
            return True
        print(f"!! JS点击{name}: 无目标", flush=True)
        return False
    except Exception as e:
        print(f"!! JS{name}: {str(e)[:60]}", flush=True)
        return False


def phys_click(fr, sel, name):
    try:
        loc = fr.locator(sel).first
        if loc.count() == 0:
            return False
        loc.scroll_into_view_if_needed(timeout=5000)
        time.sleep(1)
        box = loc.bounding_box()
        if not box:
            return False
        fr.page.mouse.click(box["x"] + box["width"] / 2, box["y"] + box["height"] / 2)
        print(f"✓ 物理点击 {name} @({int(box['x']+box['width']/2)},{int(box['y']+box['height']/2)})", flush=True)
        time.sleep(2.5)
        return True
    except Exception as e:
        print(f"!! 物理{name}: {str(e)[:60]}", flush=True)
        return False


JS_CUS = """()=>{
    const c=document.querySelector('span.cus');
    if(!c) return false;
    c.scrollIntoView({block:'center'});
    c.click();
    return true;
}"""

JS_CARD = """()=>{
    // 找包含"自定义"的套餐卡片（class含card）
    const cards=[...document.querySelectorAll('[class*="card"]')];
    for(const c of cards){
        const t=(c.innerText||'');
        if(t.includes('自定义')&&t.includes('24小时')&&t.length<120){
            c.scrollIntoView({block:'center'});
            c.click();
            return true;
        }
    }
    return false;
}"""

JS_NAME = """()=>{
    const ns=[...document.querySelectorAll('div.name')].filter(n=>(n.innerText||'').trim()==='自定义');
    if(!ns.length) return false;
    ns[0].scrollIntoView({block:'center'});
    (ns[0].parentElement||ns[0]).click();
    ns[0].click();
    return true;
}"""

JS_SWITCH = """()=>{
    const ss=[...document.querySelectorAll('span,a,div')].filter(e=>(e.innerText||'').trim()==='切换至自定义'&&e.children.length<=1);
    if(!ss.length) return false;
    ss[0].scrollIntoView({block:'center'});
    ss[0].click();
    return true;
}"""

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

    st0 = state(fr)
    print(f"初始: {json.dumps(st0, ensure_ascii=False)}", flush=True)
    a0 = amounts(fr)
    print(f"初始金额: {a0}", flush=True)

    # 多策略尝试激活自定义
    activated = False
    strategies = [
        ("JS cus", lambda: js_click(fr, JS_CUS, "span.cus 自定义勾选")),
        ("JS card", lambda: js_click(fr, JS_CARD, "自定义卡片")),
        ("JS name+parent", lambda: js_click(fr, JS_NAME, "自定义name父级")),
        ("物理 cus", lambda: phys_click(fr, 'span.cus', "span.cus")),
        ("JS switch", lambda: js_click(fr, JS_SWITCH, "切换至自定义")),
        ("物理 switch", lambda: phys_click(fr, 'text=切换至自定义', "切换至自定义")),
    ]
    for sname, fn in strategies:
        try:
            fn()
        except Exception as e:
            print(f"!! {sname}: {str(e)[:60]}", flush=True)
            continue
        shot(pg, f"g_{sname.replace(' ','_')}")
        st = state(fr)
        am = amounts(fr)
        print(f"[{sname}] vis={len(st['vis'])} num={st['num'][:20]} dialog={st['hasDialog']} amts={am}", flush=True)
        # 自定义激活判据：出现可见输入框，或金额列表出现新值(非50/100/300)，或出现弹窗含输入
        new_amt = [a for a in am if a not in (50.0, 100.0, 300.0)]
        if st["vis"] or new_amt or (st["hasDialog"] and st["vis"]):
            activated = True
            print(f"✓✓ 策略 {sname} 激活了自定义!", flush=True)
            break

    if not activated:
        print("!! 所有策略均未激活自定义，最后截图", flush=True)
        shot(pg, "g_fail")
    else:
        st = state(fr)
        # 填239
        filled = False
        for i, v in enumerate(st["vis"]):
            sel = 'input:visible' if v["tag"] == "INPUT" else '[contenteditable="true"]'
            try:
                el = fr.locator(sel).nth(i)
                el.click()
                time.sleep(0.5)
                if v["tag"] == "INPUT":
                    el.fill("239")
                else:
                    pg.keyboard.type("239", delay=30)
                filled = True
                print(f"✓ 填入239 ({v})", flush=True)
                break
            except Exception as e:
                print(f"fill err{i}: {str(e)[:50]}", flush=True)
        if filled:
            pg.keyboard.press("Enter")
            time.sleep(3)
        shot(pg, "g2_filled")
        am = amounts(fr)
        st = state(fr)
        print(f"填后: amts={am} paybar={st['paybar']} vis={len(st['vis'])}", flush=True)

        ok = (not filled) or any(abs(a - 239) < 0.01 for a in am) or "239" in st["paybar"]
        if not ok:
            print("!! 金额未变239，中止支付", flush=True)
            shot(pg, "g_abort")
        else:
            # 点底部立即支付
            phys_click(fr, 'button:has-text("立即支付")', "底部立即支付")
            time.sleep(4)
            shot(pg, "g3_paypanel")
            am2 = amounts(fr)
            st2 = state(fr)
            print(f"弹窗: amts={am2} dialog={st2['hasDialog']}", flush=True)

            # B币支付
            for sel in ['text=B币支付']:
                try:
                    loc = fr.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click()
                        print("✓ 选B币支付", flush=True)
                        time.sleep(2)
                        break
                except Exception:
                    continue
            shot(pg, "g4_bcoin")

            am3 = amounts(fr)
            if any(abs(a - 239) < 0.01 for a in am3):
                clicked = False
                locs = fr.locator('button:has-text("立即支付")')
                for i in range(locs.count()):
                    try:
                        if locs.nth(i).is_visible():
                            locs.nth(i).click()
                            clicked = True
                            print(f"✓ 弹窗立即支付 #{i}", flush=True)
                            time.sleep(5)
                            break
                    except Exception:
                        continue
                shot(pg, "g5_after_pay")
                st3 = state(fr)
                print(f"支付后: dialog={st3['hasDialog']} paybar={st3['paybar']}", flush=True)
                for sel in ['button:has-text("确定")', 'text=我知道了', 'button:has-text("完成")']:
                    try:
                        loc = fr.locator(sel).first
                        if loc.count() > 0 and loc.is_visible():
                            loc.click()
                            print(f"✓ 收尾点击 {sel}", flush=True)
                            time.sleep(3)
                            break
                    except Exception:
                        continue
                shot(pg, "g6_final")
            else:
                print(f"!! 弹窗金额非239: {am3}，取消", flush=True)
                shot(pg, "g_abort2")
                try:
                    fr.locator('button:has-text("取消")').first.click()
                except Exception:
                    pass

    time.sleep(12)
    ctx.close()

#!/usr/bin/env python3
"""必火推广v8：纯坐标方案。切换自定义→填239→校验¥239→B币支付"""
import time, json, re
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"

# 页面绝对坐标（1440x900视口，来自截图×1.40625）
XY_SWITCH = (1290, 480)     # 右上角"切换至自定义"链接
XY_PAYBAR = (1218, 859)     # 底部支付栏"立即支付"按钮


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


def dump(sc, tag):
    try:
        info = sc.evaluate("""()=>{
            const lines=[];
            document.body.innerText.split('\\n').forEach(l=>{
                const t=l.trim();
                if(t && t.length<50 && /实付|支付|预算|自定义|投入|¥|确认/.test(t)) lines.push(t);
            });
            const inputs=[];
            document.querySelectorAll('input,[contenteditable="true"]').forEach(e=>{
                const r=e.getBoundingClientRect();
                if(r.width>0) inputs.push({tag:e.tagName,type:e.type||'',val:(e.value||'').slice(0,20),ph:e.placeholder||''});
            });
            return {lines:lines.slice(0,25),inputs:inputs.slice(0,10)};
        }""")
        print(f"[dump:{tag}] {json.dumps(info, ensure_ascii=False)}", flush=True)
        return info
    except Exception as e:
        print(f"[dump err:{tag}] {str(e)[:60]}", flush=True)
        return {"inputs": []}


def get_amount(sc):
    """从当前可见文本中提取'确认订单并支付'弹窗里的¥金额，以及实付金额"""
    try:
        t = sc.evaluate("()=>document.body.innerText")
        m = re.findall(r"[¥￥]\s*([0-9]+(?:\.[0-9]{1,2})?)", t or "")
        return [float(x) for x in m]
    except Exception:
        return []


def try_click(sc, sel, name, phys=False):
    try:
        loc = sc.locator(sel).first
        if loc.count() == 0 or not loc.is_visible():
            return False
        if phys:
            box = loc.bounding_box()
            if not box:
                return False
            # iframe偏移补偿：元素在页面上 = frame内坐标 + frame_offset
            off = sc.evaluate("""()=>{
                const f=window.frameElement;
                if(!f) return {x:0,y:0};
                const r=f.getBoundingClientRect();
                return {x:Math.round(r.x),y:Math.round(r.y)};
            }""")
            x = box["x"] + box["width"] / 2 + off.get("x", 0)
            y = box["y"] + box["height"] / 2 + off.get("y", 0)
            sc.page.mouse.click(x, y)
        else:
            loc.click()
        print(f"✓ 点击 {name}", flush=True)
        time.sleep(2.5)
        return True
    except Exception as e:
        print(f"!! 点击{name}: {str(e)[:60]}", flush=True)
        return False


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

    # 1) 坐标点击"切换至自定义"
    pg.mouse.click(*XY_SWITCH)
    print(f"✓ 坐标点击切换至自定义 {XY_SWITCH}", flush=True)
    time.sleep(3)
    shot(pg, "e1_switch")
    st = dump(fr, "after_switch")

    # 2) 填自定义预算 239
    filled = False
    for attempt in range(4):
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
        # frame偏移补偿后的物理输入
        try:
            box = fr.locator("input:visible").first.bounding_box()
            if box:
                off = fr.evaluate("""()=>{const f=window.frameElement;if(!f)return{x:0,y:0};const r=f.getBoundingClientRect();return{x:Math.round(r.x),y:Math.round(r.y)};}""")
                pg.mouse.click(box["x"] + off.get("x", 0) + 40, box["y"] + off.get("y", 0) + box["height"] / 2)
                time.sleep(0.5)
                pg.keyboard.type("239", delay=30)
                filled = True
                print(f"✓ 坐标输入239 @({box['x']+off.get('x',0)},{box['y']+off.get('y',0)})", flush=True)
                break
        except Exception:
            pass
        time.sleep(2)
    shot(pg, "e2_filled")

    if filled:
        pg.keyboard.press("Enter")
        time.sleep(2.5)
    dump(fr, "after_fill")
    shot(pg, "e3_paybar")
    amounts = get_amount(fr)
    print(f"页面¥金额: {amounts}", flush=True)

    # 3) 校验239后点底部立即支付
    ok = filled and any(abs(a - 239) < 0.01 for a in amounts)
    if not ok:
        print(f"!! 未确认239金额 (filled={filled}, amounts={amounts})，中止", flush=True)
        shot(pg, "e_abort")
    else:
        pg.mouse.click(*XY_PAYBAR)
        print(f"✓ 坐标点击底部立即支付 {XY_PAYBAR}", flush=True)
        time.sleep(4)
        shot(pg, "e4_paypanel")
        pd = dump(fr, "pay_frame")
        amounts2 = get_amount(fr)
        print(f"支付弹窗¥金额: {amounts2}", flush=True)

        # 4) 确保B币支付选中
        bcoin = False
        for sel in ['text=B币支付', '[class*="bcoin"]']:
            try:
                loc = fr.locator(sel).first
                if loc.count() > 0 and loc.is_visible():
                    loc.click()
                    bcoin = True
                    print("✓ 选B币支付", flush=True)
                    time.sleep(2)
                    break
            except Exception:
                continue
        shot(pg, "e5_bcoin")

        # 5) 弹窗金额必须是239才点立即支付
        amounts3 = get_amount(fr)
        print(f"确认金额: {amounts3}", flush=True)
        if any(abs(a - 239) < 0.01 for a in amounts3):
            clicked = False
            for sel in ['button:has-text("立即支付")', 'text=立即支付']:
                try:
                    locs = fr.locator(sel)
                    for i in range(locs.count()):
                        loc = locs.nth(i)
                        if loc.is_visible():
                            loc.click()
                            clicked = True
                            print(f"✓ 点击弹窗立即支付 #{i}", flush=True)
                            time.sleep(5)
                            break
                    if clicked:
                        break
                except Exception:
                    continue
            shot(pg, "e6_after_pay")
            dump(fr, "after_pay")
            # 可能有二次确认
            for sel in ['button:has-text("确定")', 'text=确定支付', 'button:has-text("确认")']:
                try:
                    loc = fr.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click()
                        print(f"✓ 二次确认 {sel}", flush=True)
                        time.sleep(4)
                        break
                except Exception:
                    continue
            shot(pg, "e7_final")
            dump(fr, "final")
        else:
            print(f"!! 弹窗金额不是239: {amounts3}，取消支付", flush=True)
            shot(pg, "e_abort2")
            try:
                fr.locator('button:has-text("取消")').first.click()
            except Exception:
                pass

    time.sleep(15)
    ctx.close()

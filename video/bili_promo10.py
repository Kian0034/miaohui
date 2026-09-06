#!/usr/bin/env python3
"""必火推广v9：offset补偿点击+侦察自定义金额组件"""
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


def frame_offset(fr):
    try:
        return fr.evaluate("""()=>{const f=window.frameElement;if(!f)return{x:0,y:0};const r=f.getBoundingClientRect();return{x:r.x,y:r.y};}""")
    except Exception:
        return {"x": 0, "y": 0}


def phys_click(fr, sel, name):
    try:
        loc = fr.locator(sel).first
        if loc.count() == 0:
            print(f"!! {name}: 未找到", flush=True)
            return False
        loc.scroll_into_view_if_needed(timeout=5000)
        time.sleep(1)
        box = loc.bounding_box()
        if not box:
            print(f"!! {name}: 无box", flush=True)
            return False
        off = frame_offset(fr)
        x = box["x"] + box["width"] / 2 + off["x"]
        y = box["y"] + box["height"] / 2 + off["y"]
        fr.page.mouse.click(x, y)
        print(f"✓ 物理点击 {name} @({int(x)},{int(y)}) off=({int(off['x'])},{int(off['y'])})", flush=True)
        time.sleep(2.5)
        return True
    except Exception as e:
        print(f"!! {name}: {str(e)[:70]}", flush=True)
        return False


def scout(fr, tag):
    """侦察：套餐/自定义区域的所有可见叶子元素"""
    try:
        info = fr.evaluate("""()=>{
            const out=[];
            const walk=(el)=>{
                for(const c of el.children){
                    const r=c.getBoundingClientRect();
                    if(r.width<=0||r.height<=0) continue;
                    const t=(c.innerText||'').trim().replace(/\\n/g,' ');
                    const hasKids=c.children.length;
                    if(!hasKids && t && t.length<60){
                        out.push({t, tag:c.tagName, cls:(c.className||'').toString().slice(0,50),
                                  x:Math.round(r.x), y:Math.round(r.y), w:Math.round(r.width), h:Math.round(r.height)});
                    }
                    walk(c);
                }
            };
            // 找"选择的套餐"卡片容器
            const all=document.querySelectorAll('div,section');
            let root=null;
            for(const d of all){
                const t=(d.innerText||'');
                if(t.includes('选择的套餐')&&t.length<800){root=d;break;}
            }
            if(root){walk(root);}
            return out.slice(0,60);
        }""")
        print(f"[scout:{tag}]", flush=True)
        for e in info:
            print(f"  {e['tag']} ({e['x']},{e['y']},{e['w']}x{e['h']}) cls={e['cls'][:30]} | {e['t'][:45]}", flush=True)
        return info
    except Exception as e:
        print(f"[scout err:{tag}] {str(e)[:60]}", flush=True)
        return []


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

    # 侦察1：切换前
    scout(fr, "before")

    # 物理点击"切换至自定义"
    phys_click(fr, 'text=切换至自定义', "切换至自定义")
    shot(pg, "f1_switch")

    # 侦察2：切换后
    scout(fr, "after")
    shot(pg, "f2_after")

    # 点击自定义卡片（若有）
    if not phys_click(fr, '[class*="card"]:has-text("自定义")', "自定义卡片"):
        scout_info = scout(fr, "retry")
    shot(pg, "f3_card")

    # 侦察3：点击后找输入/编辑组件
    scout(fr, "after_card")

    # 全页找所有input/编辑器（包括隐藏的）
    try:
        allin = fr.evaluate("""()=>{
            const out=[];
            document.querySelectorAll('input,textarea,[contenteditable]').forEach(e=>{
                const r=e.getBoundingClientRect();
                out.push({tag:e.tagName,type:e.type||'',ph:e.placeholder||'',vis:r.width>0,
                          x:Math.round(r.x),y:Math.round(r.y),cls:(e.className||'').toString().slice(0,40)});
            });
            return out.slice(0,15);
        }""")
        print(f"[all inputs] {json.dumps(allin, ensure_ascii=False)}", flush=True)
    except Exception as e:
        print(f"all inputs err: {str(e)[:60]}", flush=True)

    time.sleep(10)
    ctx.close()

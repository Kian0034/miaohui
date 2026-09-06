#!/usr/bin/env python3
"""找必火推广真实入口URL"""
import time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/home", wait_until="domcontentloaded", timeout=60000)
    time.sleep(9)

    # 找侧边栏必火推广元素信息
    info = pg.evaluate("""()=>{
        const out = [];
        const walk = (n)=>{
            for (const c of n.children) walk(c);
            const t = (n.innerText||'').trim();
            if (t === '必火推广' && n.children.length === 0) {
                const r = n.getBoundingClientRect();
                let href = null, cls = (n.className||'').toString();
                let p = n;
                for (let i=0;i<4 && p;i++){ if(p.tagName==='A' && p.href){href=p.href;break;} p=p.parentElement; }
                out.push({tag:n.tagName, cls:cls.slice(0,60), href, x:r.x, y:r.y, vis:r.width>0});
            }
        };
        walk(document.body);
        return out;
    }""")
    print(json.dumps(info, ensure_ascii=False, indent=1), flush=True)

    # 点击并观察URL/frames变化
    pg.locator('text=必火推广').first.click()
    for i in range(10):
        time.sleep(3)
        urls = [f.url[:75] for f in pg.frames]
        if any("fly-pc" in u or "cm.bilibili" in u for u in urls):
            print(f"iframe出现 ({i*3}s)", flush=True)
            break
    print("当前页URL:", pg.url[:90], flush=True)
    for f in pg.frames:
        print("  frame:", f.url[:80], flush=True)
    pg.screenshot(path=f"{SHOTS}/nav_cur.png")
    ctx.close()

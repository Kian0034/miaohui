#!/usr/bin/env python3
"""查BV号+稿件编辑页结构（投票弹幕入口侦察）"""
import time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()

    # 方法1: 稿件管理页原始HTML找bvid
    pg.goto("https://member.bilibili.com/platform/upload-manager/article",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)
    bvid = pg.evaluate("""()=>{
        const html = document.body.innerHTML;
        const m = html.match(/bvid=(BV[0-9A-Za-z]{10})/);
        return m ? m[1] : (html.match(/BV[0-9A-Za-z]{10}/)||[])[0]||null;
    }""")
    print("BV:", bvid, flush=True)

    # 方法2: 页面文本看状态
    txt = pg.evaluate("()=>document.body.innerText.slice(0,900)")
    print(txt[:500], flush=True)

    if bvid:
        pg.goto(f"https://member.bilibili.com/platform/upload-manager/article-edit?t=1&bvid={bvid}",
                wait_until="domcontentloaded", timeout=60000)
        time.sleep(12)
        pg.screenshot(path=f"{SHOTS}/e1_edit.png")
        # 找互动弹幕/投票相关入口
        for fr in pg.frames:
            if "bilibili.com" not in (fr.url or ""):
                continue
            try:
                items = fr.evaluate("""()=>{
                    const out=[];
                    document.querySelectorAll('a,button,[class*="tab"],[class*="menu"],[role="tab"]').forEach(e=>{
                        const t=(e.innerText||'').trim();
                        if(t && t.length<14 && /弹幕|互动|投票|高级|更多/.test(t)) {
                            const r=e.getBoundingClientRect();
                            out.push({t, tag:e.tagName, vis:r.width>0, href:e.href||''});
                        }
                    });
                    return out;
                }""")
                if items:
                    print(json.dumps(items, ensure_ascii=False, indent=1), flush=True)
            except Exception:
                pass
    ctx.close()

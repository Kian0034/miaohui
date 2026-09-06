#!/usr/bin/env python3
"""深度状态检查：稿件真实审核状态（含退稿检测）"""
import time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
BV = "BVHgBzVhbcto"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/upload-manager/article",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(9)

    r = pg.evaluate("""async ()=>{
        const r = await fetch('https://member.bilibili.com/x/vupre/web/archive/list?pn=1&ps=5&status=all',
            {credentials:'include', headers:{'accept':'application/json'}});
        const t = await r.text();
        try { return JSON.parse(t); } catch(e) { return {code:-999, raw: t.slice(0,200)}; }
    }""")
    print("list code:", r.get("code"), "msg:", r.get("message"), flush=True)
    data = r.get("data") or {}
    for a in data.get("arc_audits") or []:
        arc = a["Archive"]
        print(json.dumps({
            "bvid": arc.get("bvid"), "title": (arc.get("title") or "")[:30],
            "state": arc.get("state"), "state_desc": arc.get("state_desc"),
            "pubtime": arc.get("pubtime"), "ctime": arc.get("ctime")
        }, ensure_ascii=False))
    # 页面文本快照
    txt = pg.evaluate("""()=>{
        const rows = [...document.querySelectorAll('div,li,span,p')].filter(e=>{
            const t=e.innerText||'';
            return t.includes('审核')||t.includes('通过')||t.includes('打回');
        });
        return rows.length? rows[0].innerText.slice(0,300): '无审核字样';
    }""")
    print("页面:", txt[:150], flush=True)
    pg.screenshot(path="/Users/ff/miaohui/video/shots/status_check.png")
    ctx.close()

#!/usr/bin/env python3
"""登录态诊断：稿件列表+状态（DOM+API双路）"""
import time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/upload-manager/article",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(15)
    print("URL:", pg.url)
    # API: 稿件列表
    r = pg.evaluate("""async ()=>{
        try{
            const lst = await fetch('https://member.bilibili.com/x/vupre/web/archive/list?pn=1&ps=20',{credentials:'include'}).then(r=>r.text());
            try{return {api:JSON.parse(lst)};}catch(e){return {raw:lst.slice(0,200)};}
        }catch(e){return {err:String(e)};}
    }""")
    if "api" in r:
        data = r["api"]
        print("list code:", data.get("code"), data.get("message", ""))
        arcs = (data.get("data") or {}).get("arc_audits") or []
        print("稿件数:", len(arcs))
        for a in arcs:
            ar = a.get("Archive") or {}
            print(" -", ar.get("bvid"), "|", (ar.get("title") or "")[:24], "|", ar.get("state_desc"), "| state:", ar.get("state"), "| pass:", a.get("Statistic", {}).get("view"))
    else:
        print("API返回非JSON:", r)
    # DOM: 页面可见文本
    txt = pg.evaluate("()=>document.body.innerText.slice(0,1200)")
    print("---DOM文本---")
    print(txt)
    pg.screenshot(path="/Users/ff/miaohui/video/shots/diag_now.png")
    ctx.close()

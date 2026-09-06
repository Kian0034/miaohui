#!/usr/bin/env python3
"""清理B站投稿页本地草稿(IndexedDB/localStorage)，保留登录Cookie"""
import time
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/upload/video/frame",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)

    # 枚举IndexedDB
    dbs = pg.evaluate("""async ()=>{
        const names = await indexedDB.databases().then(l=>l.map(d=>d.name));
        return names;
    }""")
    print("IndexedDB:", dbs, flush=True)

    # 删除与草稿/上传相关的库
    for name in dbs:
        low = name.lower()
        if any(k in low for k in ["draft", "videoup", "upload", "archive", "preup"]):
            pg.evaluate(f"""async ()=>{{ await indexedDB.deleteDatabase('{name}'); }}""")
            print("已删除DB:", name, flush=True)

    # localStorage相关key
    ls = pg.evaluate("""()=>{
        const out=[];
        for (let i=0;i<localStorage.length;i++){const k=localStorage.key(i);out.push(k);}
        return out;
    }""")
    print("localStorage keys:", ls, flush=True)
    pg.evaluate("""()=>{
        const kill=[];
        for (let i=0;i<localStorage.length;i++){const k=localStorage.key(i);
            if(/draft|upload|videoup|archive/i.test(k)) kill.push(k);}
        kill.forEach(k=>localStorage.removeItem(k));
        return kill.length;
    }""")
    # sessionStorage也清
    pg.evaluate("()=>{sessionStorage.clear()}")

    # 刷新验证
    pg.reload(wait_until="domcontentloaded")
    time.sleep(8)
    bar = pg.evaluate("()=>document.body.innerText.includes('未提交的视频')")
    print("刷新后草稿提示条仍存在:", bar, flush=True)
    pg.screenshot(path="/Users/ff/miaohui/video/shots/cleaned.png")
    ctx.close()

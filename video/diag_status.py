#!/usr/bin/env python3
"""诊断：登录态+稿件状态+必火订单状态"""
import json, time
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        args=["--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/upload/video",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)
    r = pg.evaluate("""async ()=>{
        const csrf=(document.cookie.match(/bili_jct=([^;]+)/)||[])[1];
        const nav=await fetch('https://api.bilibili.com/x/web-interface/nav',{credentials:'include'}).then(r=>r.json());
        const lst=await fetch('https://member.bilibili.com/x/vupre/web/archive/list?pn=1&ps=10',{credentials:'include'}).then(r=>r.json());
        const arcs=(lst.data&&lst.data.arc_audits)||[];
        const view=await fetch('https://api.bilibili.com/x/web-interface/view?bvid=BVHgBzVhbcto',{credentials:'include'}).then(r=>r.json());
        return {
            login: nav.data&&nav.data.isLogin? nav.data.uname : 'NOT_LOGIN',
            arcCount: arcs.length,
            arcs: arcs.map(a=>({t:(a.Archive||{}).title||'', bv:(a.Archive||{}).bvid||'', st:(a.Archive||{}).state_desc||'', code:(a.Archive||{}).state})),
            viewCode: view.code, viewMsg: view.message,
            viewState: view.data? view.data.state : null,
            viewAid: view.data? view.data.aid : null
        };
    }""")
    print(json.dumps(r, ensure_ascii=False, indent=1))
    ctx.close()

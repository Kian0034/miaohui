#!/usr/bin/env python3
"""精确侦察：找上传视频按钮真实DOM和所有file input"""
import os, time, json
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
    pg.goto("https://member.bilibili.com/platform/upload/video/frame",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)

    for i, fr in enumerate(pg.frames):
        try:
            info = fr.evaluate("""()=>{
              const out = {files: [], texts: [], iframes: []};
              document.querySelectorAll('input[type=file]').forEach(e=>{
                const r = e.getBoundingClientRect();
                out.files.push({cls:(e.className||'').slice(0,40), accept:(e.accept||'').slice(0,40),
                  vis: r.width>0, parentCls:(e.parentElement?.className||'').toString().slice(0,60)});
              });
              // 找所有包含"上传视频"的叶子元素
              const walk = (n)=>{
                for (const c of n.children) walk(c);
                if (n.children.length===0 && (n.textContent||'').includes('上传视频')) {
                  const r = n.getBoundingClientRect();
                  out.texts.push({tag:n.tagName, cls:(n.className||'').toString().slice(0,60),
                    vis:r.width>0&&r.height>0, x:r.x, y:r.y});
                }
              };
              walk(document.body);
              document.querySelectorAll('iframe').forEach(f=>out.iframes.push(f.src.slice(0,80)));
              return out;
            }""")
            if info["files"] or info["texts"] or info["iframes"]:
                print(f"--- frame{i}: {fr.url[:70]}")
                print(json.dumps(info, ensure_ascii=False, indent=1)[:1500])
        except Exception as e:
            print(f"frame{i} err: {str(e)[:80]}")
    ctx.close()

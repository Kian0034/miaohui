#!/usr/bin/env python3
"""秒回MiaoHui B站投稿：侦察阶段——上传视频并dump表单结构"""
import os, sys, time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
VIDEO = "/Users/ff/miaohui/video/output/final_v1.mp4"
SHOTS = "/Users/ff/miaohui/video/shots"
os.makedirs(SHOTS, exist_ok=True)

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=True, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.set_default_timeout(30000)

    pg.goto("https://member.bilibili.com/platform/upload/video/frame",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(6)

    # 找file input并上传
    fi = None
    for fr in pg.frames:
        try:
            loc = fr.locator('input[type="file"]')
            if loc.count() > 0:
                fi = loc.first
                break
        except Exception:
            pass
    if fi:
        fi.set_input_files(VIDEO)
        print("[ok] 视频已选择，等待上传+转码...", flush=True)
    else:
        print("[err] 没找到file input"); ctx.close(); sys.exit(1)

    # 等待表单（标题输入框）
    form = False
    for i in range(60):
        for fr in pg.frames:
            try:
                if fr.locator('input[placeholder*="标题"]').count() > 0:
                    form = True
                    break
            except Exception:
                pass
        if form:
            print(f"[ok] 表单就绪 ({i*3}s)", flush=True)
            break
        time.sleep(3)
    time.sleep(5)
    pg.screenshot(path=f"{SHOTS}/r1_form.png", full_page=False)

    # dump所有label和控件
    dump = []
    for fr in pg.frames:
        if "bilibili.com" not in (fr.url or ""):
            continue
        try:
            items = fr.evaluate("""()=>{
              const out=[];
              document.querySelectorAll('input,textarea,[contenteditable="true"],.bcc-select,[class*="select-input"],[class*="radio"],[class*="checkbox"]').forEach(e=>{
                const r=e.getBoundingClientRect();
                if(r.width<=0&&r.height<=0) return;
                out.push({
                  tag:e.tagName,
                  type:e.type||'',
                  ph:e.placeholder||'',
                  val:(e.value||'').slice(0,40),
                  txt:(e.innerText||'').slice(0,60).replace(/\\n/g,'|'),
                  cls:(e.className||'').toString().slice(0,60),
                  checked:e.checked===true?1:0
                });
              });
              return out;
            }""")
            dump.append({"frame": fr.url[:60], "items": items[:80]})
        except Exception as e:
            dump.append({"frame": fr.url[:60], "err": str(e)[:100]})
    print(json.dumps(dump, ensure_ascii=False, indent=1))
    ctx.close()

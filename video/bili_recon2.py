#!/usr/bin/env python3
"""秒回MiaoHui B站投稿：v2侦察——filechooser方式上传+等待表单+dump结构"""
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

    # 关掉草稿提示条(点"不用了"仅收起，不删除)
    for sel in ['text=不用了', 'text=继续编辑']:
        try:
            loc = pg.locator(sel).first
            if sel == 'text=不用了' and loc.count() > 0 and loc.is_visible():
                loc.click()
                print("[ok] 已关闭草稿提示条", flush=True)
                time.sleep(1)
                break
        except Exception:
            pass

    # 点击上传按钮 + filechooser
    btn = None
    for sel in ['button:has-text("上传视频")', 'text=上传视频', '.upload-btn']:
        try:
            loc = pg.locator(sel).first
            if loc.count() > 0 and loc.is_visible():
                btn = loc
                break
        except Exception:
            pass
    if not btn:
        print("[err] 找不到上传按钮")
        pg.screenshot(path=f"{SHOTS}/r2_nobtn.png")
        ctx.close(); sys.exit(1)

    with pg.expect_file_chooser(timeout=15000) as fc:
        btn.click()
    fc.value.set_files(VIDEO)
    print("[ok] 文件已选中，上传开始...", flush=True)

    # 等表单（最多5分钟）
    form = False
    for i in range(100):
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
        if i % 10 == 9:
            print(f"  ...等待中 {i*3}s", flush=True)
        time.sleep(3)
    time.sleep(5)
    pg.screenshot(path=f"{SHOTS}/r2_form.png")

    # dump
    dump = []
    for fr in pg.frames:
        if "bilibili.com" not in (fr.url or ""):
            continue
        try:
            items = fr.evaluate("""()=>{
              const out=[];
              document.querySelectorAll('input,textarea,[contenteditable="true"]').forEach(e=>{
                const r=e.getBoundingClientRect();
                const hidden = r.width<=0&&r.height<=0;
                if(hidden && e.type!=='file') return;
                out.push({tag:e.tagName,type:e.type||'',ph:e.placeholder||'',
                  val:(e.value||'').slice(0,50),cls:(e.className||'').toString().slice(0,50)});
              });
              // 可见文本按钮
              document.querySelectorAll('button,[class*="btn"],[class*="radio"],[class*="select"]').forEach(e=>{
                const r=e.getBoundingClientRect();
                if(r.width<=0) return;
                const t=(e.innerText||'').trim().slice(0,30);
                if(t) out.push({tag:'UI',cls:(e.className||'').toString().slice(0,40),txt:t});
              });
              return out.slice(0,100);
            }""")
            dump.append({"frame": fr.url[:50], "n": len(items), "items": items})
        except Exception as e:
            dump.append({"frame": fr.url[:50], "err": str(e)[:100]})
    with open(f"{SHOTS}/form_dump.json", "w") as f:
        json.dump(dump, f, ensure_ascii=False, indent=1)
    print("[ok] 结构已存 form_dump.json", flush=True)
    ctx.close()

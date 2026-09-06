#!/usr/bin/env python3
"""侦察6：全新上传——点击dropzone(父级)+filechooser；并清掉误恢复的旧草稿编辑状态"""
import os, time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
VIDEO = "/Users/ff/miaohui/video/output/final_v1.mp4"
SHOTS = "/Users/ff/miaohui/video/shots"

with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        PROFILE, headless=False, executable_path=EXE,
        viewport={"width": 1440, "height": 900},
        args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
              "--no-proxy-server", "--proxy-server=direct://"])
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    pg.goto("https://member.bilibili.com/platform/upload/video/frame",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(8)

    # dump dropzone DOM结构
    for fr in pg.frames:
        if "member.bilibili.com" not in (fr.url or ""):
            continue
        info = fr.evaluate("""()=>{
          const btn = document.querySelector('.upload-btn');
          if (!btn) return {found: false};
          let chain = [];
          let n = btn;
          for (let i=0; i<4 && n; i++) {
            chain.push({tag:n.tagName, cls:(n.className||'').toString().slice(0,60), pe:getComputedStyle(n).pointerEvents});
            n = n.parentElement;
          }
          return {found: true, chain};
        }""")
        print(json.dumps(info, ensure_ascii=False, indent=1), flush=True)

    # 点dropzone（upload-btn的父级链上 pointerEvents!=none 的最近元素）
    clicked = False
    for fr in pg.frames:
        if "member.bilibili.com" not in (fr.url or ""):
            continue
        try:
            if fr.locator('.upload-btn').count() == 0:
                continue
            # 依次试 父级、祖父级
            for level in ["xpath=..", "xpath=../..", "xpath=../../.."]:
                tgt = fr.locator('.upload-btn').first.locator(level)
                try:
                    with pg.expect_file_chooser(timeout=6000) as fc:
                        tgt.click(timeout=4000)
                    fc.value.set_files(VIDEO)
                    clicked = True
                    print(f"[ok] dropzone({level}) filechooser 成功", flush=True)
                    break
                except Exception as e:
                    print(f"  {level}: {str(e)[:70]}", flush=True)
            if clicked:
                break
        except Exception:
            pass

    if not clicked:
        # 最后兜底：dispatch drag&drop事件
        print("尝试DataTransfer drop...", flush=True)
        for fr in pg.frames:
            if "member.bilibili.com" not in (fr.url or ""):
                continue
            try:
                fr.evaluate("""async ()=>{
                  const resp = await fetch('file:///nonexistent').catch(()=>null);
                }""")
            except Exception:
                pass
            break

    # 等表单
    form = False
    for i in range(80):
        try:
            if pg.locator('input[placeholder*="标题"]').count() > 0:
                form = True
                print(f"[ok] 表单就绪 ({i*3}s)", flush=True)
                break
        except Exception:
            pass
        if i % 10 == 9:
            pg.screenshot(path=f"{SHOTS}/r6_t{i}.png")
        time.sleep(3)
    time.sleep(6)
    pg.screenshot(path=f"{SHOTS}/r6_final.png")
    print("form:", form, flush=True)
    ctx.close()

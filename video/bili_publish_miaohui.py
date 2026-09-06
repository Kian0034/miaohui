#!/usr/bin/env python3
"""秒回MiaoHui B站投稿 FINAL：dropzone filechooser上传 + 全字段填写 + 验证门 + 提交"""
import os, sys, time, json
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
VIDEO = "/Users/ff/miaohui/video/output/final_v1.mp4"
COVER = "/Users/ff/miaohui/video/output/cover.png"
SHOTS = "/Users/ff/miaohui/video/shots"
os.makedirs(SHOTS, exist_ok=True)
SUBMIT = os.environ.get("SUBMIT", "0") == "1"

TITLE = '微软Recall被打穿后，我自己写了个「秒回」：0.3秒找回电脑里任何一帧，纯本地·开源·免费'
DESC = """你电脑里几万张截图、几千个视频，想找其中一帧要翻多久？

「秒回 MiaoHui」是一个纯本地的照片/截图/视频搜索引擎：
· 视频帧级索引：直接跳回原视频 07:21 那一帧
· OCR：截图里的文字全都能搜
· ASR：视频里说过的话也能搜，精确到秒
· 全程离线，一个字节都不上传，缩略图AES-256加密
· 银行、密码管理器默认不索引，审计日志可查

⬇️ Mac 版下载（夸克网盘）：
https://pan.quark.cn/s/fef677cdd18b

开源仓库：https://github.com/Kian0034/miaohui

时间轴：
00:00 你也有这个问题
00:08 实测：红衣跳舞→07:21
00:20 搜截图文字（OCR）
00:28 搜视频里的话（ASR）
00:38 Rewind/Screenpipe/Recall 都怎么了
00:58 原理：三路检索+本地向量
01:12 隐私怎么保证
01:26 下载方式

#秒回 #本地搜索 #开源软件 #效率工具 #程序员"""
TAGS = ["秒回", "本地搜索", "开源软件", "效率工具", "程序员", "软件推荐", "桌面搜索"]


def shot(pg, name):
    try:
        pg.screenshot(path=f"{SHOTS}/{name}.png", timeout=8000)
        print(f"[shot] {name}", flush=True)
    except Exception as e:
        print(f"[shot err] {e}", flush=True)


def find_in_frames(pg, sel):
    for fr in pg.frames:
        try:
            loc = fr.locator(sel)
            if loc.count() > 0:
                return loc.first, fr
        except Exception:
            pass
    return None, None


def find_visible(pg, selectors):
    for s in selectors:
        for fr in pg.frames:
            try:
                loc = fr.locator(s)
                for i in range(min(loc.count(), 5)):
                    if loc.nth(i).is_visible():
                        return loc.nth(i), fr
            except Exception:
                pass
    return None, None


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=False, executable_path=EXE,
            viewport={"width": 1440, "height": 900},
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
                  "--no-proxy-server", "--proxy-server=direct://"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()
        pg.set_default_timeout(30000)

        # === 1. 打开投稿页 ===
        print("[1] 打开投稿页", flush=True)
        pg.goto("https://member.bilibili.com/platform/upload/video/frame",
                wait_until="domcontentloaded", timeout=60000)
        time.sleep(6)

        # === 2. 上传: 点 .upload-btn 父级(.upload-area) + filechooser ===
        print("[2] 上传视频", flush=True)
        ok = False
        for fr in pg.frames:
            if "member.bilibili.com" not in (fr.url or ""):
                continue
            try:
                if fr.locator('.upload-btn').count() == 0:
                    continue
                tgt = fr.locator('.upload-btn').first.locator("xpath=..")
                with pg.expect_file_chooser(timeout=10000) as fc:
                    tgt.click(timeout=5000)
                fc.value.set_files(VIDEO)
                ok = True
                print("  ✓ dropzone filechooser", flush=True)
                break
            except Exception as e:
                print(f"  尝试失败: {str(e)[:70]}", flush=True)
        if not ok:
            shot(pg, "f_fail_upload")
            ctx.close()
            sys.exit(1)

        # 等表单+上传完成
        form = False
        for i in range(100):
            try:
                if pg.locator('input[placeholder*="标题"]').count() > 0:
                    form = True
                    if i > 2:
                        print(f"  ✓ 表单就绪 ({i*3}s)", flush=True)
                    break
            except Exception:
                pass
            time.sleep(3)
        if not form:
            print("  !! 表单未出现", flush=True)
            shot(pg, "f_no_form")
            ctx.close()
            sys.exit(1)
        # 等上传100%
        print("  等待上传100%...", flush=True)
        for i in range(60):
            try:
                done = pg.evaluate("""()=>document.body.innerText.includes('100%')||document.body.innerText.includes('上传完成')""")
                if done:
                    print(f"  ✓ 上传完成 ({i*3}s)", flush=True)
                    break
            except Exception:
                pass
            time.sleep(3)
        time.sleep(4)
        shot(pg, "f1_uploaded")

        # === 3. 标题 ===
        print("[3] 标题", flush=True)
        t_loc, _ = find_in_frames(pg, 'input[placeholder*="标题"]')
        try:
            cur = t_loc.input_value(timeout=3000)
            if cur.strip() != TITLE:
                t_loc.click()
                t_loc.fill("")
                t_loc.type(TITLE, delay=8)
                print(f"  ✓ 标题已填({len(TITLE)}字)", flush=True)
            else:
                print("  ✓ 标题已正确", flush=True)
        except Exception as e:
            print(f"  err: {str(e)[:80]}", flush=True)
        time.sleep(1)

        # === 4. 创作声明 ===
        print("[4] 创作声明", flush=True)
        try:
            d_loc, _ = find_in_frames(pg, 'input[placeholder*="创作声明"]')
            if d_loc:
                cur = d_loc.input_value(timeout=2000)
                if "无需标注" in cur:
                    print("  ✓ 已是内容无需标注", flush=True)
                else:
                    d_loc.click()
                    time.sleep(2)
                    opt, _ = find_visible(pg, ['.bcc-option:has-text("内容无需标注")'])
                    if opt:
                        opt.click()
                        time.sleep(1.5)
                        print("  ✓ 选择内容无需标注", flush=True)
            else:
                print("  !! 声明框未找到", flush=True)
        except Exception as e:
            print(f"  err: {str(e)[:80]}", flush=True)

        # === 5. 简介 ===
        print("[5] 简介", flush=True)
        try:
            d_loc, _ = find_visible(pg, ['.ql-editor'])
            if d_loc:
                cur = d_loc.inner_text().strip()
                if "pan.quark.cn" not in cur:
                    d_loc.click()
                    time.sleep(0.5)
                    pg.keyboard.type(DESC, delay=1)
                    print("  ✓ 简介已填", flush=True)
                else:
                    print("  ✓ 简介已填过", flush=True)
            else:
                print("  !! 简介框未找到", flush=True)
        except Exception as e:
            print(f"  err: {str(e)[:80]}", flush=True)
        time.sleep(1)

        # === 6. 标签 ===
        print("[6] 标签", flush=True)
        try:
            tg_loc, _ = find_visible(pg, ['input[placeholder*="回车"]', 'input[placeholder*="标签"]'])
            if tg_loc:
                for tg in TAGS:
                    tg_loc.click()
                    tg_loc.fill("")
                    tg_loc.type(tg, delay=15)
                    pg.keyboard.press("Enter")
                    time.sleep(0.6)
                print(f"  ✓ {len(TAGS)}个标签", flush=True)
            else:
                print("  !! 标签框未找到", flush=True)
        except Exception as e:
            print(f"  err: {str(e)[:80]}", flush=True)
        time.sleep(1)

        # === 7. 封面 ===
        print("[7] 封面", flush=True)
        try:
            cov, _ = find_visible(pg, ['text=添加封面', '.cover-empty', '.cover-empty-pill'])
            if cov:
                cov.click()
                time.sleep(3)
                dialog = False
                for i in range(15):
                    for fr in pg.frames:
                        try:
                            if fr.locator('.cover-editor.bcc-dialog__wrap-mask:visible').count() > 0:
                                dialog = True
                                break
                        except Exception:
                            pass
                    if dialog:
                        break
                    time.sleep(1)
                print(f"  封面弹窗: {dialog}", flush=True)
                if dialog:
                    time.sleep(2)
                    done = False
                    for fr in pg.frames:
                        try:
                            if fr.locator('.cover-editor:visible').count() == 0:
                                continue
                            up = None
                            for sel in ['text=上传封面', '[class*="upload-area"]', 'text=拖拽图片或点击上传']:
                                l = fr.locator(sel).first
                                if l.count() > 0 and l.is_visible():
                                    up = l
                                    break
                            if up:
                                with pg.expect_file_chooser(timeout=8000) as fc:
                                    up.click()
                                fc.value.set_files(COVER)
                                done = True
                                print("  ✓ 封面已上传(filechooser)", flush=True)
                                break
                        except Exception:
                            continue
                    if not done:
                        for fr in pg.frames:
                            try:
                                ins = fr.locator('.cover-editor input[type="file"]')
                                if ins.count() > 0:
                                    ins.first.set_input_files(COVER)
                                    done = True
                                    print("  ✓ 封面已上传(input)", flush=True)
                                    break
                            except Exception:
                                pass
                    time.sleep(5)
                    shot(pg, "f2_cover_dialog")
                    for a in range(4):
                        okb, _ = find_visible(pg, ['.cover-editor-button .submit',
                                                   '.cover-editor-content-right-bottom .submit'])
                        if okb:
                            okb.click()
                            time.sleep(2)
                        closed = True
                        for fr in pg.frames:
                            try:
                                if fr.locator('.cover-editor.bcc-dialog__wrap-mask:visible').count() > 0:
                                    closed = False
                                    break
                            except Exception:
                                pass
                        if closed:
                            print("  ✓ 封面弹窗已关闭", flush=True)
                            break
            else:
                print("  封面可能已设置", flush=True)
        except Exception as e:
            print(f"  err: {str(e)[:80]}", flush=True)
        time.sleep(2)
        shot(pg, "f3_filled")

        # === 8. 验证门 ===
        print("\n[8] 验证", flush=True)
        passed = True
        try:
            t_loc, _ = find_in_frames(pg, 'input[placeholder*="标题"]')
            tv = t_loc.input_value() if t_loc else ""
            print(f"  标题({len(tv)}字): {tv[:40]}...", flush=True)
            if "秒回" not in tv:
                passed = False
        except Exception:
            passed = False
        for fr in pg.frames:
            try:
                dt = fr.locator('.ql-editor').first.inner_text()
                if dt.strip():
                    link_ok = "pan.quark.cn/s/fef677cdd18b" in dt
                    print(f"  简介链接正确: {link_ok} ({len(dt)}字)", flush=True)
                    if not link_ok:
                        passed = False
                    break
            except Exception:
                continue
        print(f"  >>> 验证{'通过' if passed else '未通过'} <<<", flush=True)

        # === 9. 提交 ===
        if SUBMIT and passed:
            print("\n[9] 提交", flush=True)
            sub, _ = find_visible(pg, ['text=立即投稿', '.submit-add', '.submit-container > div:last-child'])
            if sub:
                sub.click()
                print("  ✓ 点击立即投稿", flush=True)
                time.sleep(5)
                shot(pg, "f4_clicked")
                for txt in ["确认投稿", "继续提交", "确认提交", "立即投稿", "确定"]:
                    okb, _ = find_visible(pg, [f'button:has-text("{txt}")', f'div:has-text("{txt}")'])
                    if okb:
                        try:
                            okb.click()
                            time.sleep(3)
                            print(f"  ✓ 二次确认: {txt}", flush=True)
                            break
                        except Exception:
                            pass
                success = False
                for w in range(60):
                    time.sleep(1)
                    if any(k in pg.url for k in ["upload-manager", "archive", "/list"]):
                        print(f"  ✓ 跳转管理页: {pg.url[:70]}", flush=True)
                        success = True
                        break
                    for fr in pg.frames:
                        try:
                            body = fr.evaluate("()=>(document.body?document.body.innerText:'').slice(0,1500)")
                            if any(t in body for t in ["投稿成功", "提交成功", "稿件已提交", "发布成功"]):
                                print(f"  ✓ 成功toast ({w}s)", flush=True)
                                success = True
                                break
                        except Exception:
                            pass
                    if success:
                        break
                shot(pg, "f5_result")
                print("\n🎉 投稿成功!" if success else "\n⚠ 未确认成功，看截图", flush=True)
            else:
                print("  !! 提交按钮未找到", flush=True)
                shot(pg, "f4_nobtn")
        else:
            print(f"\n[未提交] SUBMIT={SUBMIT} passed={passed}", flush=True)
            time.sleep(30)

        ctx.storage_state(path="/Users/ff/vdown_promo/work/bili_state.json")
        ctx.close()


if __name__ == "__main__":
    main()

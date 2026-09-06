#!/usr/bin/env python3
"""黄金一小时监控v3：登录自愈（弹窗扫码）+ 修正BV + 降频防风控"""
import time, json, os, random, subprocess
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
STATE = "/Users/ff/miaohui/video/gh_state.json"
LOGF = "/Users/ff/miaohui/video/gh.log"
BV = open("/Users/ff/miaohui/video/real_bv.txt").read().strip() if os.path.exists("/Users/ff/miaohui/video/real_bv.txt") else "BV7vvTjHGDNz"

PIN_COMMENT = ("你们最想一键找回的是什么？截图？聊天记录里的图？还是某节课的录屏？"
               "评论区告诉我，点赞最高的需求，我下期优先做（手机版安排中）。"
               "前10秒有个彩蛋，看谁先发现 👀")

DYN_TEXT = ("做了一个纯本地的「秒回」搜索引擎：0.3秒找回电脑里任何一帧画面，\n"
            "截图文字、视频里说的话都能搜，全程离线不上传。\n"
            "开源免费，Mac版今天发布 👇\n#效率工具# #开源软件# #本地搜索#")


def log(*a):
    line = f"[{time.strftime('%H:%M:%S')}] " + " ".join(str(x) for x in a)
    print(line, flush=True)
    with open(LOGF, "a") as f:
        f.write(line + "\n")


def notify(title, msg):
    try:
        subprocess.Popen(["osascript", "-e",
                          f'display notification "{msg}" with title "{title}" sound name "Glass"'],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        pass


def save(st):
    with open(STATE, "w") as f:
        json.dump(st, f, ensure_ascii=False, indent=1)


def page_txt(pg):
    try:
        return pg.evaluate("()=>document.body.innerText.slice(0,400)")
    except Exception:
        return ""


def check_login(pg):
    """打开member页判断登录态，返回(bool, arcs)"""
    pg.goto("https://member.bilibili.com/platform/upload-manager/article",
            wait_until="domcontentloaded", timeout=60000)
    time.sleep(10)
    txt = page_txt(pg)
    if "扫码登录" in txt:
        return False, []
    arcs = []
    try:
        r = pg.evaluate("""async ()=>{
            const l = await fetch('https://member.bilibili.com/x/vupre/web/archive/list?pn=1&ps=20',
                {credentials:'include'}).then(r=>r.json());
            return l;
        }""")
        arcs = (r.get("data") or {}).get("arc_audits") or []
    except Exception as e:
        log("列表err:", str(e)[:60])
    return True, arcs


def golden_hour(ctx, pg, state):
    aid = state["aid"]
    def api(method, path, body=None):
        return pg.evaluate("""async ([method, path, body])=>{
            const csrf = (document.cookie.match(/bili_jct=([^;]+)/)||[])[1];
            const opt = {method, credentials:'include', headers:{}};
            if (body) {
                opt.headers['Content-Type'] = 'application/x-www-form-urlencoded';
                const p = new URLSearchParams({...body, csrf});
                opt.body = p.toString();
            }
            const r = await fetch(path, opt);
            const t = await r.text();
            try { return JSON.parse(t); } catch(e) { return {code:-999, raw:t.slice(0,120)}; }
        }""", [method, path, body])

    if not state.get("liked"):
        r1 = api("POST", "https://api.bilibili.com/x/web-interface/archive/like",
                 {"bvid": BV, "like": "1"})
        state["liked"] = r1.get("code") == 0
        log("点赞:", r1.get("code"), str(r1.get("message", ""))[:20])
        time.sleep(2)
    if not state.get("coined"):
        r2 = api("POST", "https://api.bilibili.com/x/web-interface/coin/add",
                 {"bvid": BV, "multiply": "1", "select_like": "1"})
        state["coined"] = r2.get("code") == 0
        log("投币:", r2.get("code"), str(r2.get("message", ""))[:20])
        time.sleep(2)
    if not state.get("faved"):
        mid = pg.evaluate("()=>(document.cookie.match(/DedeUserID=(\\d+)/)||[])[1]")
        folders = api("GET", f"https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={mid}")
        fid = None
        if folders.get("code") == 0 and folders.get("data"):
            fid = folders["data"][0]["id"]
        if fid:
            r3 = api("POST", "https://api.bilibili.com/x/v3/fav/resource/deal",
                     {"rid": str(aid), "type": "2", "add_media_ids": str(fid)})
            state["faved"] = r3.get("code") == 0
            log("收藏:", r3.get("code"), str(r3.get("message", ""))[:20])
            time.sleep(2)
    if not state.get("commented"):
        r4 = api("POST", "https://api.bilibili.com/x/v2/reply/add",
                 {"oid": str(aid), "type": "1", "message": PIN_COMMENT, "platform": "pc"})
        state["commented"] = r4.get("code") == 0
        rpid = (r4.get("data") or {}).get("rpid")
        log("评论:", r4.get("code"), str(r4.get("message", ""))[:20], "rpid:", rpid)
        if rpid:
            time.sleep(3)
            r5 = api("POST", "https://api.bilibili.com/x/v2/reply/top",
                     {"oid": str(aid), "type": "1", "rpid": str(rpid), "action": "1"})
            state["pinned"] = r5.get("code") == 0
            log("置顶:", r5.get("code"), str(r5.get("message", ""))[:30])
    save(state)

    if not state.get("dyn"):
        try:
            pg2 = ctx.new_page()
            pg2.goto("https://t.bilibili.com/", wait_until="domcontentloaded", timeout=60000)
            time.sleep(6)
            for sel in ['.ql-editor', '[contenteditable="true"]']:
                try:
                    loc = pg2.locator(sel).first
                    if loc.count() > 0 and loc.is_visible():
                        loc.click()
                        time.sleep(1)
                        pg2.keyboard.type(DYN_TEXT, delay=5)
                        time.sleep(1)
                        for bsel in ['button:has-text("发布")', 'text=发布']:
                            try:
                                bl = pg2.locator(bsel).first
                                if bl.count() > 0 and bl.is_visible() and bl.is_enabled():
                                    bl.click()
                                    state["dyn"] = True
                                    log("✓ 动态已发布")
                                    break
                            except Exception:
                                continue
                        break
                except Exception:
                    continue
            time.sleep(4)
            pg2.screenshot(path="/Users/ff/miaohui/video/shots/dyn_result.png")
            pg2.close()
        except Exception as e:
            log("动态err:", str(e)[:80])
        save(state)


def main():
    state = {"bvid": BV, "aid": None, "passed": False, "liked": False,
             "coined": False, "faved": False, "commented": False, "pinned": False,
             "dyn": False}
    try:
        state.update(json.load(open(STATE)))
        if state.get("bvid") != BV:
            state["bvid"] = BV
            state["passed"] = False  # BV修正后重新判定
    except Exception:
        pass
    save(state)

    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=True, executable_path=EXE,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
                  "--no-proxy-server", "--proxy-server=direct://"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()

        # ---- 登录自愈：未登录则弹窗等扫码（最多10分钟），否则headless继续 ----
        ok, arcs = check_login(pg)
        if not ok:
            log("登录态失效，弹窗等待扫码（10分钟）...")
            notify("秒回MiaoHui", "B站登录已失效，弹出窗口请扫码登录，监控将自动恢复")
            try:
                ctx.close()
            except Exception:
                pass
            ctx = p.chromium.launch_persistent_context(
                PROFILE, headless=False, executable_path=EXE,
                args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
                      "--no-proxy-server", "--proxy-server=direct://"])
            pg = ctx.pages[0] if ctx.pages else ctx.new_page()
            pg.goto("https://member.bilibili.com/platform/upload-manager/article",
                    wait_until="domcontentloaded", timeout=60000)
            try:
                pg.bring_to_front()
            except Exception:
                pass
            ok = False
            for i in range(200):  # 10分钟
                time.sleep(3)
                txt = page_txt(pg)
                if "扫码登录" not in txt and ("稿件" in txt or "数据" in txt or "上传" in txt):
                    ok = True
                    log(f"✓ 用户扫码登录成功（第{i*3}秒）")
                    break
            if ok:
                with open("/Users/ff/miaohui/video/login_ok.flag", "w") as f:
                    f.write(time.strftime("%Y-%m-%d %H:%M:%S"))
            else:
                log("✗ 扫码超时，转入headless轮询（每20分钟弹通知提醒）")
        if ok:
            time.sleep(2)
            _, arcs = check_login(pg)

        # 打印当前稿件状态
        for a in arcs:
            ar = a.get("Archive") or {}
            log("稿件:", ar.get("bvid"), "|", (ar.get("title") or "")[:20], "|", ar.get("state_desc"))

        # ---- 主轮询：6小时，90s±抖动 ----
        last_notify = 0
        for i in range(240):
            if state.get("passed") and state.get("dyn"):
                break
            v = pg.evaluate("""async (bv)=>{
                try{
                    const r = await fetch(`https://api.bilibili.com/x/web-interface/view?bvid=${bv}`,
                        {credentials:'include'}).then(r=>r.json());
                    return {code:r.code, aid:(r.data||{}).aid, msg:r.message};
                }catch(e){return {code:-998, msg:String(e).slice(0,40)};}
            }""", BV)
            if v.get("code") == 0 and v.get("aid"):
                if not state.get("passed"):
                    state["aid"] = v["aid"]
                    state["passed"] = True
                    save(state)
                    log("✓✓ 审核通过! aid=", state["aid"])
                    notify("秒回MiaoHui", "视频审核通过！正在执行黄金一小时运营动作")
                    golden_hour(ctx, pg, state)
                break
            # view=-400时用稿件列表辅助判断（登录态下能看到真实状态）
            desc = ""
            if i % 5 == 0:
                try:
                    r = pg.evaluate("""async ()=>{
                        const l = await fetch('https://member.bilibili.com/x/vupre/web/archive/list?pn=1&ps=20',
                            {credentials:'include'}).then(r=>r.json());
                        return l;
                    }""")
                    for a in (r.get("data") or {}).get("arc_audits") or []:
                        ar = a.get("Archive") or {}
                        if ar.get("bvid") == BV:
                            desc = ar.get("state_desc", "")
                            st = ar.get("state")
                            if st in (0, -30):  # 0=公开 -30=等待转正
                                pass
                except Exception:
                    pass
            now = time.time()
            if not ok and now - last_notify > 1200:
                notify("秒回MiaoHui", "B站仍未登录，弹出Chrome窗口扫码即可恢复监控")
                last_notify = now
            log(f"poll{i}: view={v.get('code')}/{str(v.get('msg',''))[:16]} 状态:{desc}")
            time.sleep(90 + random.randint(0, 30))

        ctx.close()
    log("结束:", json.dumps(state, ensure_ascii=False))


if __name__ == "__main__":
    main()

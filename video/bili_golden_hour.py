#!/usr/bin/env python3
"""黄金一小时运营：轮询审核→(通过后)三连+置顶评论+状态上报"""
import time, json, re, sys
from playwright.sync_api import sync_playwright

PROFILE = "/Users/ff/vdown_promo/work/browser_profile"
EXE = "/Users/ff/Applications/chrome-mac-arm64/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing"
SHOTS = "/Users/ff/miaohui/video/shots"
STATE = "/Users/ff/miaohui/video/gh_state.json"

PIN_COMMENT = ("你们最想一键找回的是什么？截图？聊天记录里的图？还是某节课的录屏？"
               "评论区告诉我，点赞最高的需求，我下期优先做（手机版安排中）。"
               "前10秒有个彩蛋，看谁先发现 👀")


def log(*a):
    print(f"[{time.strftime('%H:%M:%S')}]", *a, flush=True)


def get_bvid(pg):
    return pg.evaluate("""async ()=>{
        // 从稿件管理页DOM找bvid
        const html = document.body.innerHTML;
        const m = html.match(/bvid=(BV[0-9A-Za-z]{10})/);
        if (m) return m[1];
        const m2 = html.match(/(BV[0-9A-Za-z]{10})/);
        return m2 ? m2[1] : null;
    }""")


def api(pg, method, path, body=None):
    return pg.evaluate("""async ([method, path, body])=>{
        const csrf = (document.cookie.match(/bili_jct=([^;]+)/)||[])[1];
        const opt = {method, credentials:'include', headers:{}};
        if (body) {
            opt.headers['Content-Type'] = 'application/x-www-form-urlencoded';
            const p = new URLSearchParams({...body, csrf});
            opt.body = p.toString();
        }
        const r = await fetch(path, opt);
        return await r.json();
    }""", [method, path, body])


def main():
    with sync_playwright() as p:
        ctx = p.chromium.launch_persistent_context(
            PROFILE, headless=True, executable_path=EXE,
            args=["--disable-blink-features=AutomationControlled", "--lang=zh-CN",
                  "--no-proxy-server", "--proxy-server=direct://"])
        pg = ctx.pages[0] if ctx.pages else ctx.new_page()

        # 1. 拿BV号
        pg.goto("https://member.bilibili.com/platform/upload-manager/article",
                wait_until="domcontentloaded", timeout=60000)
        time.sleep(8)
        bvid = get_bvid(pg)
        if not bvid:
            log("!! 没找到BV号")
            pg.screenshot(path=f"{SHOTS}/gh_nobvid.png")
            ctx.close()
            sys.exit(1)
        log("BV号:", bvid)
        aid = None

        # 2. 轮询审核（最长40分钟）
        passed = False
        for i in range(40):
            v = api(pg, "GET", f"https://api.bilibili.com/x/web-interface/view?bvid={bvid}")
            if v.get("code") == 0 and v.get("data", {}).get("aid"):
                aid = v["data"]["aid"]
                passed = True
                log(f"✓ 审核通过! aid={aid} 标题: {v['data']['title'][:30]}")
                break
            else:
                log(f"审核中... ({i+1}/40) code={v.get('code')} msg={v.get('message','')[:30]}")
            time.sleep(60)

        state = {"bvid": bvid, "aid": aid, "passed": passed, "liked": False,
                 "coined": False, "faved": False, "commented": False, "pinned": False}

        if passed and aid:
            # 3. 三连（点赞+投币+收藏，各一次）
            r1 = api(pg, "POST", "https://api.bilibili.com/x/web-interface/archive/like",
                     {"bvid": bvid, "like": "1"})
            state["liked"] = r1.get("code") == 0
            log("点赞:", r1.get("code"), r1.get("message", "")[:20])

            r2 = api(pg, "POST", "https://api.bilibili.com/x/web-interface/coin/add",
                     {"bvid": bvid, "multiply": "1", "select_like": "1"})
            state["coined"] = r2.get("code") == 0
            log("投币:", r2.get("code"), r2.get("message", "")[:20])

            # 默认收藏夹
            mid = pg.evaluate("()=>(document.cookie.match(/DedeUserID=(\\d+)/)||[])[1]")
            folders = api(pg, "GET",
                          f"https://api.bilibili.com/x/v3/fav/folder/created/list-all?up_mid={mid}")
            fid = None
            if folders.get("code") == 0 and folders.get("data"):
                fid = folders["data"][0]["id"]
            if fid:
                r3 = api(pg, "POST", "https://api.bilibili.com/x/v3/fav/resource/deal",
                         {"rid": str(aid), "type": "2", "add_media_ids": str(fid)})
                state["faved"] = r3.get("code") == 0
                log("收藏:", r3.get("code"), r3.get("message", "")[:20])

            # 4. 置顶评论
            r4 = api(pg, "POST", "https://api.bilibili.com/x/v2/reply/add",
                     {"oid": str(aid), "type": "1", "message": PIN_COMMENT, "platform": "pc",
                      "csrf": ""})
            state["commented"] = r4.get("code") == 0
            rpid = (r4.get("data") or {}).get("rpid")
            log("评论:", r4.get("code"), r4.get("message", "")[:20], "rpid:", rpid)

            if rpid:
                time.sleep(3)
                r5 = api(pg, "POST", "https://api.bilibili.com/x/v2/reply/top",
                         {"oid": str(aid), "type": "1", "rpid": str(rpid), "action": "1"})
                state["pinned"] = r5.get("code") == 0
                log("置顶:", r5.get("code"), r5.get("message", "")[:30])

        with open(STATE, "w") as f:
            json.dump(state, f, ensure_ascii=False, indent=1)
        log("状态:", json.dumps(state, ensure_ascii=False))
        ctx.close()


if __name__ == "__main__":
    main()

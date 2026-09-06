"""局域网检索服务：手机/平板浏览器免安装检索 PC 全量索引。

  python3 main.py --serve            # 默认 0.0.0.0:7788
  python3 main.py --serve --port 9000

接口：
  GET  /               手机友好的 PWA 检索页（可添加到主屏幕）
  GET  /api/ping       {app, device, index_size, latency_hint}
  GET  /api/search?q=&limit=    检索结果 JSON（含缩略图 base64）
  GET  /api/open?path=&ts=      在本机打开原文件/视频跳时间点
"""
import base64
import json
import socket
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs, unquote

from . import config

_PORT = 7788
_SRV = None

_PAGE = """<!doctype html>
<html lang="zh-CN"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="theme-color" content="#0b0c10">
<title>秒回 MiaoHui</title>
<style>
*{box-sizing:border-box;margin:0;padding:0;-webkit-tap-highlight-color:transparent}
body{background:#0b0c10;color:#e8eaed;font-family:-apple-system,"PingFang SC","HarmonyOS Sans",sans-serif;
  min-height:100vh;padding-bottom:env(safe-area-inset-bottom)}
.hd{text-align:center;padding:38px 16px 10px}
.hd h1{font-size:34px;font-weight:800;letter-spacing:1px}
.hd h1 .m{color:#ff3d81}
.hd p{color:#8a8f98;font-size:13px;margin-top:6px}
.bar{position:sticky;top:0;z-index:9;background:rgba(11,12,16,.92);backdrop-filter:blur(12px);
  padding:12px 14px 10px;display:flex;gap:8px}
.bar input{flex:1;height:46px;border-radius:14px;border:1px solid #2a2d35;background:#16181d;
  color:#fff;font-size:16px;padding:0 16px;outline:none}
.bar input:focus{border-color:#ff3d81}
.bar .go{height:46px;padding:0 20px;border-radius:14px;border:0;background:linear-gradient(135deg,#ff3d81,#ff6a3d);
  color:#fff;font-size:16px;font-weight:700}
.stat{color:#565b64;font-size:12px;text-align:center;padding:2px 0 8px}
.list{display:grid;gap:12px;padding:6px 14px 30px;max-width:640px;margin:0 auto}
.card{display:flex;gap:12px;background:#14161b;border:1px solid #22252d;border-radius:16px;
  padding:10px;cursor:pointer}
.card:active{border-color:#ff3d81}
.thumb{width:96px;height:72px;border-radius:10px;background:#1d2026;object-fit:cover;flex:none;
  display:flex;align-items:center;justify-content:center;color:#565b64;font-size:11px}
.thumb.vid{position:relative}
.thumb.vid:after{content:"▶";position:absolute;font-size:20px;color:rgba(255,255,255,.9)}
.info{flex:1;min-width:0}
.path{font-size:13px;font-weight:600;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.sub{color:#8a8f98;font-size:12px;margin-top:3px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.tag{display:inline-block;background:#1f2129;color:#9aa0aa;border-radius:6px;font-size:10px;
  padding:1px 6px;margin:4px 6px 0 0}
.ts{color:#ff3d81;font-weight:700}
.empty{text-align:center;color:#565b64;padding:70px 30px;font-size:14px;line-height:2}
.hint{color:#565b64;font-size:11px;text-align:center;padding:8px 16px 20px}
</style></head><body>
<div class="hd"><h1>秒回<span class="m">MiaoHui</span></h1>
<p id="dev">正在连接电脑…</p></div>
<div class="bar">
<input id="q" type="search" placeholder="搜画面、搜截图文字、搜视频里说的话…" autocomplete="off">
<button class="go" onclick="go()">搜索</button></div>
<div class="stat" id="stat"></div>
<div class="list" id="list"></div>
<div class="empty" id="empty">输入关键词回车搜索<br>截图文字 · 视频台词 · 画面内容 · 文件名<br>
0.3 秒定位到那一帧，跳回电脑原文件</div>
<div class="hint">iPhone：Safari 打开本页 → 分享 → 添加到主屏幕，即可像 App 一样使用</div>
<script>
let base='';
const fmt=s=>{s=Math.round(s);return `${Math.floor(s/60)}:${String(s%60).padStart(2,'0')}`};
const esc=t=>(t||'').replace(/[<>&"]/g,c=>({'<':'&lt;','>':'&gt;','&':'&amp;','"':'&quot;'}[c]));
async function ping(){
  try{
    const r=await fetch(base+'/api/ping');const j=await r.json();
    document.getElementById('dev').textContent=j.device+' · 索引 '+j.index_size.toLocaleString()+' 项 · 本地检索 '+j.latency_hint;
  }catch(e){document.getElementById('dev').textContent='连接失败：请确认电脑端秒回已启动且同一WiFi';}
}
function card(it){
  const d=document.createElement('div');d.className='card';
  const th=it.thumb?`<img class="thumb ${it.kind==='video'?'vid':''}" src="data:image/jpeg;base64,${it.thumb}">`
    :`<div class="thumb ${it.kind==='video'?'vid':''}">${it.kind==='video'?'视频':'文件'}</div>`;
  const meta=[it.date||'',it.kind==='video'&&it.dur?fmt(it.dur):''].filter(Boolean).join(' · ');
  d.innerHTML=`${th}<div class="info">
    <div class="path">${esc(it.name)}</div>
    <div class="sub">${esc(meta)}</div>
    ${it.ts!=null?`<span class="tag ts">第 ${fmt(it.ts)}</span>`:''}
    ${it.ocr?`<span class="tag">文字 ${esc(it.ocr.slice(0,20))}</span>`:''}
    ${it.asr?`<span class="tag">台词 ${esc(it.asr.slice(0,20))}</span>`:''}
  </div>`;
  d.onclick=()=>{location.href=`/api/open?path=${encodeURIComponent(it.path)}${it.ts!=null?'&ts='+it.ts:''}`};
  return d;
}
async function go(){
  const q=document.getElementById('q').value.trim();if(!q)return;
  const st=document.getElementById('stat');
  st.textContent='检索中…';
  try{
    const t0=Date.now();
    const r=await fetch(base+'/api/search?q='+encodeURIComponent(q)+'&limit=40');
    const j=await r.json();
    st.textContent=`${j.results.length} 个结果 · 电脑端耗时 ${j.latency_ms}ms · 索引 ${j.index_size.toLocaleString()} 项`;
    const L=document.getElementById('list');L.innerHTML='';
    document.getElementById('empty').style.display=j.results.length?'none':'block';
    j.results.forEach(it=>L.appendChild(card(it)));
  }catch(e){st.textContent='检索失败：'+e;}
}
document.getElementById('q').addEventListener('keydown',e=>{if(e.key==='Enter')go()});
ping();
</script></body></html>"""


def _local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("223.5.5.5", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def _start():
    global _SRV
    if _SRV is not None:
        return _SRV

    service = {"obj": None}

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def _json(self, obj, code=200):
            b = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(b)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(b)

        def do_GET(self):
            u = urlparse(self.path)
            q = parse_qs(u.query)
            try:
                if u.path == "/":
                    b = _PAGE.encode()
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html; charset=utf-8")
                    self.send_header("Content-Length", str(len(b)))
                    self.end_headers()
                    self.wfile.write(b)
                elif u.path == "/api/ping":
                    from .search import SearchService
                    if service["obj"] is None:
                        service["obj"] = SearchService()
                    self._json({
                        "app": "MiaoHui", "device": f"{socket.gethostname()}（Mac/PC 端）",
                        "index_size": service["obj"].vis.count + service["obj"].txt.count,
                        "latency_hint": "<0.3s",
                    })
                elif u.path == "/api/search":
                    query = unquote((q.get("q") or [""])[0]).strip()
                    limit = min(int((q.get("limit") or ["40"])[0]), 100)
                    if not query:
                        return self._json({"results": [], "latency_ms": 0, "index_size": 0})
                    from .search import SearchService
                    if service["obj"] is None:
                        service["obj"] = SearchService()
                    r = service["obj"].search(query, limit=limit)
                    from . import config
                    out = []
                    for it in r["results"]:
                        p = Path(it["path"])
                        rec = {
                            "id": it["id"], "score": it["score"],
                            "name": p.name, "path": str(p),
                            "kind": it["kind"], "ts": it["ts"], "dur": it["dur"],
                            "ocr": it.get("ocr") or "", "asr": it.get("asr") or "",
                            "date": time.strftime("%Y-%m-%d", time.localtime(p.stat().st_mtime)) if p.exists() else "",
                        }
                        if it.get("thumb"):
                            rec["thumb"] = base64.b64encode(it["thumb"]).decode()
                        out.append(rec)
                    self._json({"results": out, "latency_ms": r["latency_ms"],
                                "index_size": r["index_size"]})
                elif u.path == "/api/open":
                    import sys as _sys
                    if _sys.platform == "win32":
                        from app_win.opener import open_result
                    else:
                        from app.opener import open_result
                    path = unquote((q.get("path") or [""])[0])
                    ts = q.get("ts")
                    if path:
                        open_result(path, float(ts[0]) if ts else None)
                        self._json({"ok": True})
                    else:
                        self._json({"ok": False, "err": "no path"}, 400)
                else:
                    self._json({"err": "not found"}, 404)
            except Exception as e:
                try:
                    self._json({"err": str(e)[:200]}, 500)
                except Exception:
                    pass

    _SRV = ThreadingHTTPServer(("0.0.0.0", _PORT), H)
    return _SRV


def run(port: int = 7788):
    global _PORT
    _PORT = port
    srv = _start()
    ip = _local_ip()
    print(f"\n[秒回] 局域网检索服务已启动")
    print(f"  手机浏览器打开  http://{ip}:{port}")
    print(f"  （iPhone/安卓/鸿蒙通用，可添加到主屏幕当 App 用）\n")
    srv.serve_forever()

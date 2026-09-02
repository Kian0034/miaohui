"""秒回 MiaoHui — 应用主入口。

  python3 main.py            # 菜单栏应用 + ⌥Space 面板
  python3 main.py --index    # 命令行：启动/继续全量索引（前台）
  python3 main.py --search "查询词"  # 命令行检索（调试/性能测试）
"""
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT))


class App:
    """粘合层：菜单栏 / 面板 / 索引子进程 / 检索服务。"""

    def __init__(self):
        self._proc = None
        self._service = None

    # ---------- 检索服务（惰性加载模型） ----------
    @property
    def service(self):
        if self._service is None:
            from core.search import SearchService
            self._service = SearchService()
        return self._service

    # ---------- 索引子进程 ----------
    def start_indexing(self, no_asr=False, max_files=None):
        if self._proc and self._proc.poll() is None:
            return
        cmd = [sys.executable, "-m", "core.pipeline"]
        if no_asr:
            cmd.append("--no-asr")
        if max_files:
            cmd.append(f"--max-files={max_files}")
        import os
        env = dict(os.environ, PYTHONPATH=str(PROJECT))
        self._proc = subprocess.Popen(
            cmd, cwd=str(PROJECT), env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def stop_indexing(self):
        if self._proc and self._proc.poll() is None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=10)
            except Exception:
                self._proc.kill()

    def toggle_indexing(self) -> bool:
        """→ 返回是否处于运行状态"""
        if self._proc and self._proc.poll() is None:
            self.stop_indexing()
            return False
        self.start_indexing()
        return True

    def stats(self) -> dict:
        try:
            from core.db import DB
            return DB().stats()
        except Exception:
            return {}

    # ---------- UI ----------
    def show_panel(self):
        if self._panel:
            self._panel.show()

    def shutdown(self):
        self.stop_indexing()

    def run_gui(self):
        from AppKit import NSApplication, NSApplicationActivationPolicyAccessory
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(NSApplicationActivationPolicyAccessory)

        from app.panel import SearchPanel
        from app.menubar import MenuBarController
        from app.hotkey import HotkeyManager
        from app import opener

        self._panel = SearchPanel.alloc().initWithService_(self)
        self._panel.on_open = lambda path, ts: opener.open_result(path, ts)
        self._panel.stats_provider = self.stats

        self._mb = MenuBarController.alloc().initWithApp_(self)

        def on_hotkey():
            self._panel.performSelectorOnMainThread_withObject_waitUntilDone_(
                "toggle", None, False)

        self._hotkey = HotkeyManager(on_hotkey)

        # 启动即后台索引（增量）
        st = self.stats()
        if st.get("files", 0) == 0:
            self.start_indexing()

        app.run()


def main():
    args = sys.argv[1:]
    if "--index" in args:
        from core.pipeline import run
        run()
        return
    if "--search" in args:
        i = args.index("--search")
        q = args[i + 1] if i + 1 < len(args) else "测试"
        from core.search import SearchService
        res = SearchService().search(q)
        import json
        out = [{k: (f"<thumb {len(v)}B>" if k == "thumb" else v)
                for k, v in r.items()} for r in res["results"]]
        print(json.dumps({"latency_ms": res["latency_ms"],
                          "breakdown": res["breakdown"],
                          "results": out[:10]}, ensure_ascii=False, indent=2))
        return
    App().run_gui()


if __name__ == "__main__":
    main()

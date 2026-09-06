"""秒回 MiaoHui — 应用主入口。

  python3 main.py            # 菜单栏应用 + ⌥Space 面板
  python3 main.py --index    # 命令行：启动/继续全量索引（前台）
  python3 main.py --search "查询词"  # 命令行检索（调试/性能测试）
"""
import subprocess
import sys
from pathlib import Path

PROJECT = Path(__file__).resolve().parent
if not getattr(sys, "frozen", False):
    sys.path.insert(0, str(PROJECT))
FROZEN = getattr(sys, "frozen", False)


def _warm(app):
    """后台预热：模型常驻 + jieba 词库加载，用户首查即达 <0.3s。"""
    try:
        app.service.search("预热")
    except Exception:
        pass


class _LazyService:
    """面板用的惰性检索服务：首次查询才加载模型，之后直通。"""

    def __init__(self, app):
        self._app = app

    def search(self, q, limit=30):
        return self._app.service.search(q, limit=limit)

    @property
    def stats(self):
        return self._app.stats()


class App:
    """粘合层：菜单栏 / 面板 / 索引子进程 / 检索服务。"""

    def __init__(self):
        self._proc = None
        self._service = None
        self.status_extra = ""

    # ---------- 检索服务（惰性加载模型） ----------
    @property
    def service(self):
        if self._service is None:
            from core.search import SearchService
            self._service = SearchService()
        return self._service

    # ---------- 索引子进程（进程组管理，杜绝 ffmpeg 孤儿进程） ----------
    def start_indexing(self, no_asr=False, max_files=None):
        if self._proc and self._proc.poll() is None:
            return
        self._set_pause_flag(False)
        if FROZEN:
            cmd = [sys.executable, "--index-worker"]
        else:
            cmd = [sys.executable, "-m", "core.pipeline"]
        if no_asr:
            cmd.append("--no-asr")
        if max_files:
            cmd.append(f"--max-files={max_files}")
        import os
        env = dict(os.environ, PYTHONPATH=str(PROJECT))
        kwargs = {}
        if sys.platform == "win32":
            flags = 0
            for name in ("CREATE_NO_WINDOW", "CREATE_NEW_PROCESS_GROUP"):
                flags |= getattr(subprocess, name, 0)
            flags |= 0x00004000  # BELOW_NORMAL_PRIORITY_CLASS：索引低优先级
            kwargs["creationflags"] = flags
        else:
            kwargs["preexec_fn"] = os.setsid  # 独立进程组，停止时整组杀光
        self._proc = subprocess.Popen(
            cmd, cwd=str(PROJECT) if not FROZEN else None, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **kwargs)

    def stop_indexing(self):
        """彻底停止：杀整个进程组（含 ffmpeg/whisper 孙进程）。"""
        proc = self._proc
        self._proc = None
        if not proc or proc.poll() is not None:
            return
        if sys.platform == "win32":
            try:
                # /T 杀进程树，/F 强制
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                               capture_output=True, timeout=15)
            except Exception:
                try:
                    proc.kill()
                except Exception:
                    pass
        else:
            import os
            import signal
            try:
                pgid = os.getpgid(proc.pid)
                os.killpg(pgid, signal.SIGTERM)
            except Exception:
                try:
                    proc.terminate()
                except Exception:
                    pass
            try:
                proc.wait(timeout=4)
            except Exception:
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    try:
                        proc.kill()
                    except Exception:
                        pass
        try:
            proc.wait(timeout=5)
        except Exception:
            pass

    # ---------- 真暂停（不杀进程，pipeline 自检标志挂起，CPU 立刻释放） ----------
    @staticmethod
    def _set_pause_flag(paused: bool):
        from core import config
        st = config.load_settings()
        st["indexing_paused"] = bool(paused)
        config.save_settings(st)

    def is_paused(self) -> bool:
        from core import config
        return bool(config.load_settings().get("indexing_paused", False))

    def set_paused(self, paused: bool):
        self._set_pause_flag(paused)
        if not paused and not (self._proc and self._proc.poll() is None):
            self.start_indexing()

    def indexing_running(self) -> bool:
        return bool(self._proc and self._proc.poll() is None)

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
        import sys as _sys
        if _sys.platform == "win32":
            self._run_gui_win()
        else:
            self._run_gui_mac()

    def _run_gui_win(self):
        from PySide6.QtCore import QTimer
        from PySide6.QtWidgets import QApplication

        qapp = QApplication.instance() or QApplication(sys.argv)
        qapp.setQuitOnLastWindowClosed(False)
        qapp.aboutToQuit.connect(self.shutdown)  # 退出/关机时杀干净索引进程树

        from app_win.panel import SearchPanel
        from app_win.tray import TrayController
        from app_win.hotkey import WinHotkeyFilter
        from app_win import opener

        self._panel = SearchPanel(self.service, self.stats)
        self._panel.on_open = lambda path, ts: opener.open_result(path, ts)

        self._tray = TrayController(self)

        def on_hotkey():
            self._panel.toggle()

        self._hotkey = WinHotkeyFilter(on_hotkey)
        qapp.installNativeEventFilter(self._hotkey)

        import threading
        threading.Thread(
            target=lambda: _warm(self), daemon=True,
            name="warmup").start()

        from core import bootstrap
        if bootstrap.models_ready():
            self.status_extra = ""
            self.start_indexing()
        else:
            self.status_extra = " · 首次启动：正在下载模型（约 500MB，走国内镜像）"
            bootstrap.ensure_async(
                on_done=lambda ok: setattr(self, "status_extra", "") or
                (ok and self.start_indexing()),
                progress=lambda msg: setattr(self, "status_extra", f" · {msg}"))

        qapp.exec()

    def _run_gui_mac(self):
        import AppKit
        import objc
        from AppKit import NSApplication, NSObject
        app = NSApplication.sharedApplication()
        app.setActivationPolicy_(getattr(
            AppKit, "NSApplicationActivationPolicyAccessory", 1))

        # 退出委托：Cmd+Q / 关机 / 注销时先杀干净索引进程树（含 ffmpeg）
        class _TermDelegate(NSObject):
            def initWithApp_(self, owner):
                self = objc.super(_TermDelegate, self).init()
                self._owner = owner
                return self

            def applicationShouldTerminate_(self, _note):
                try:
                    self._owner.shutdown()
                except Exception:
                    pass
                return True

        app.setDelegate_(_TermDelegate.alloc().initWithApp_(self))

        from app.panel import SearchPanel
        from app.menubar import MenuBarController
        from app.hotkey import HotkeyManager
        from app import opener

        self._panel = SearchPanel.alloc().initWithService_(
            _LazyService(self))
        self._panel.on_open = lambda path, ts: opener.open_result(path, ts)
        self._panel.stats_provider = self.stats

        self._mb = MenuBarController.alloc().initWithApp_(self)

        def on_hotkey():
            self._panel.performSelectorOnMainThread_withObject_waitUntilDone_(
                "toggle", None, False)

        self._hotkey = HotkeyManager(on_hotkey)

        # 预热检索服务（CLIP/jieba 冷加载 ~5s，挪到后台，保证首查 <0.3s）
        import threading
        threading.Thread(
            target=lambda: _warm(self), daemon=True,
            name="warmup").start()

        # 模型自举：缺模型先在后台下载，就绪后再启动索引
        from core import bootstrap
        if bootstrap.models_ready():
            self.status_extra = ""
            self.start_indexing()
        else:
            self.status_extra = " · 首次启动：正在下载模型（约 500MB，走国内镜像）"
            bootstrap.ensure_async(
                on_done=lambda ok: setattr(self, "status_extra", "") or
                (ok and self.start_indexing()),
                progress=lambda msg: setattr(self, "status_extra", f" · {msg}"))

        app.run()


def main():
    args = sys.argv[1:]
    if "--probe-ui" in args:  # 冻结包 UI 导入自检（平台分支）
        import platform
        if platform.system() == "Windows":
            from app_win.panel import SearchPanel  # noqa: F401
            from app_win.tray import TrayController    # noqa: F401
            from app_win.hotkey import WinHotkeyFilter  # noqa: F401
            from app_win import opener                   # noqa: F401
        else:
            from app.panel import SearchPanel           # noqa: F401
            from app.menubar import MenuBarController   # noqa: F401
            from app.hotkey import HotkeyManager         # noqa: F401
            from app import opener                       # noqa: F401
        print("UI-PROBE OK")
        try:  # windowed exe 退出码不可靠，用标记文件判定
            with open("ui_probe_ok.txt", "w") as f:
                f.write("ok")
        except Exception:
            pass
        return
    if "--index-worker" in args:  # 冻结包内的索引子进程
        from core.pipeline import run
        run()
        return
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
        out = [{k: (f"<thumb {len(v)}B>" if k == "thumb" and v else v)
                for k, v in r.items()} for r in res["results"]]
        print(json.dumps({"latency_ms": res["latency_ms"],
                          "breakdown": res["breakdown"],
                          "results": out[:10]}, ensure_ascii=False, indent=2))
        return
    if "--serve" in args:
        port = 7788
        if "--port" in args:
            i = args.index("--port")
            if i + 1 < len(args):
                port = int(args[i + 1])
        from core.serve import run
        run(port=port)
        return
    App().run_gui()


if __name__ == "__main__":
    main()

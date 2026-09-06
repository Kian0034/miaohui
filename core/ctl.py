"""索引运行控制（暂停/停止）跨模块共享标志。

独立成模块避免 pipeline <-> scanner 循环导入。
- 停止：SIGTERM/SIGINT 置位，所有工作循环尽快退出
- 暂停：settings.json 的 indexing_paused 标志，工作循环挂起睡眠（CPU 归零）
"""
import time

from . import config

_stop = False
_pause_cache = {"paused": False, "ts": 0.0}


def request_stop():
    global _stop
    _stop = True


def stopped() -> bool:
    return _stop


def is_paused() -> bool:
    """3 秒缓存读一次暂停标志，避免高频刷 settings 文件。"""
    now = time.time()
    if now - _pause_cache["ts"] > 3:
        try:
            _pause_cache["paused"] = bool(
                config.load_settings().get("indexing_paused", False))
        except Exception:
            pass
        _pause_cache["ts"] = now
    return _pause_cache["paused"]


def gate() -> bool:
    """工作单元前调用：暂停则挂起（释放 CPU），停止则返回 True。"""
    if _stop:
        return True
    if is_paused():
        while not _stop and is_paused():
            time.sleep(0.5)
    return _stop

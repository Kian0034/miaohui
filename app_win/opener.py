"""Windows 结果打开器：图片/文件直接打开；视频有 mpv/PotPlayer 时跳秒。"""
import os
import subprocess
import sys

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".flv",
              ".wmv", ".ts", ".3gp", ".mpg", ".mpeg"}

_MPV_CANDIDATES = [
    os.path.expandvars(r"%ProgramFiles%\mpv\mpv.exe"),
    os.path.expandvars(r"%ProgramFiles(x86)%\mpv\mpv.exe"),
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\mpv\mpv.exe"),
    r"C:\PotPlayer\PotPlayerMini64.exe",
    os.path.expandvars(r"%ProgramFiles%\PotPlayer\PotPlayerMini64.exe"),
]


def _find_player():
    for p in _MPV_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS


def open_result(path: str, ts=None):
    if is_video(path) and ts is not None:
        player = _find_player()
        if player and "mpv" in player.lower():
            try:
                subprocess.Popen([player, f"--start={int(ts)}", path])
                return
            except Exception:
                pass
        if player and "potplayer" in player.lower():
            try:
                subprocess.Popen([player, path, f"/seek={int(ts):06d}"])
                return
            except Exception:
                pass
    os.startfile(path)  # noqa: S606


def reveal_in_finder(path: str):
    """Windows：资源管理器定位文件。"""
    subprocess.Popen(["explorer", "/select,", os.path.normpath(path)])


def open_default(path: str):
    os.startfile(path)  # noqa: S606

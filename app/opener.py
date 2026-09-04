"""结果打开器：图片直接打开；视频跳转到第 N 秒（QuickTime AppleScript）。

有 IINA/mpv 时优先使用（seek 更稳），否则 QuickTime，最后兜底 open。
"""
import os
import subprocess

VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".flv",
              ".wmv", ".ts", ".3gp", ".mpg", ".mpeg"}

_MPV_CANDIDATES = [
    "/opt/homebrew/bin/mpv", "/usr/local/bin/mpv",
    "/Applications/IINA.app/Contents/MacOS/iina",
    "/Applications/mpv.app/Contents/MacOS/mpv",
]


def _find_player():
    for p in _MPV_CANDIDATES:
        if os.path.exists(p):
            return p
    return None


def is_video(path: str) -> bool:
    return os.path.splitext(path)[1].lower() in VIDEO_EXTS


def open_result(path: str, ts=None):
    """打开结果；视频带时间戳则跳转播放。"""
    if is_video(path) and ts is not None:
        if _open_video_at(path, float(ts)):
            return
    _open_default(path)


def reveal_in_finder(path: str):
    from AppKit import NSWorkspace
    from Foundation import NSURL
    NSWorkspace.sharedWorkspace().activateFileViewerSelectingURLs_(
        [NSURL.fileURLWithPath_(path)])


def _open_default(path: str):
    from AppKit import NSWorkspace
    NSWorkspace.sharedWorkspace().openFile_(path)


def _open_video_at(path: str, ts: float) -> bool:
    player = _find_player()
    if player and "IINA" in player:
        # IINA: iina --mpv-seek=123 /path
        try:
            subprocess.Popen([player, f"--mpv-seek={int(ts)}", path])
            return True
        except Exception:
            pass
    elif player and "mpv" in player:
        try:
            subprocess.Popen([player, f"--start={int(ts)}", path])
            return True
        except Exception:
            pass
    # QuickTime（mp4/mov/m4v 支持度高）
    if os.path.splitext(path)[1].lower() in {".mp4", ".mov", ".m4v"}:
        try:
            # QuickTime Player 的 current time 单位为秒；bounds 防止窗口
            # 落到独立的全屏 Space 上导致看不到画面
            sc = f'''
            tell application "QuickTime Player"
                activate
                open POSIX file "{path}"
                delay 1.0
                try
                    set bounds of front window to {{280, 180, 1640, 1110}}
                end try
                try
                    set current time of front document to {int(ts)}
                    play front document
                end try
            end tell
            '''
            r = subprocess.run(["osascript", "-e", sc], capture_output=True,
                               timeout=15)
            return r.returncode == 0
        except Exception:
            pass
    return False

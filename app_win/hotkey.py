"""Windows 全局热键 Ctrl+Alt+Space（RegisterHotKey + Qt 原生事件过滤器）。"""
import ctypes
import ctypes.wintypes

from PySide6.QtCore import QAbstractNativeEventFilter

MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
VK_SPACE = 0x20
WM_HOTKEY = 0x0312
HOTKEY_ID = 0x4D48  # 'MH'


class WinHotkeyFilter(QAbstractNativeEventFilter):
    """注册全局热键，触发时回调（在主线程消息循环里，安全更新 UI）。"""

    def __init__(self, on_trigger):
        super().__init__()
        self.on_trigger = on_trigger
        self._msg = None
        user32 = ctypes.windll.user32
        if not user32.RegisterHotKey(None, HOTKEY_ID,
                                     MOD_CONTROL | MOD_ALT, VK_SPACE):
            raise OSError("RegisterHotKey failed (可能被占用)")

    def nativeEventFilter(self, event_type, message):
        if event_type == b"windows_generic_MSG":
            msg = ctypes.wintypes.MSG.from_address(int(message))
            if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                try:
                    self.on_trigger()
                except Exception:
                    pass
        return False, 0

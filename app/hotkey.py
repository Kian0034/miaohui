"""全局热键 ⌥Space（Carbon RegisterEventHotKey，系统级，可抑制）。"""
import ctypes
from ctypes import CFUNCTYPE, POINTER, byref, c_int, c_uint32, c_void_p

_carbon = ctypes.CDLL("/System/Library/Frameworks/Carbon.framework/Carbon")

# 常量
kEventClassKeyboard = 0x6B657962  # 'keyb'
kEventHotKeyPressed = 6
optionKey = 0x0800
spaceKeyCode = 49

_HandlerProc = CFUNCTYPE(c_int, c_void_p, c_void_p, c_void_p)

_carbon.RegisterEventHotKey.restype = c_int
_carbon.RegisterEventHotKey.argtypes = [c_uint32, c_uint32, c_void_p,
                                        c_void_p, c_uint32, POINTER(c_uint32)]
_carbon.InstallEventHandler.restype = c_int
_carbon.InstallEventHandler.argtypes = [c_void_p, _HandlerProc, c_uint32,
                                        c_void_p, c_void_p, POINTER(c_void_p)]
_carbon.GetApplicationEventTarget.restype = c_void_p


class HotkeyManager:
    def __init__(self, on_trigger):
        self.on_trigger = on_trigger
        self._cb = _HandlerProc(self._handler)  # 防 GC
        self._ref = None
        self._hkref = c_uint32(0)
        self._install()

    def _handler(self, callref, event, userdata):
        try:
            self.on_trigger()
        except Exception:
            pass
        return 0

    def _install(self):
        # EventTypeSpec: {class, kind} 两个 uint32
        events = (c_uint32 * 2)(kEventClassKeyboard, kEventHotKeyPressed)
        ref = c_void_p(0)
        _carbon.InstallEventHandler(
            _carbon.GetApplicationEventTarget(), self._cb, 1,
            ctypes.cast(events, c_void_p), None, byref(ref))
        # EventHotKeyID {signature='MHUI', id=1}
        hkid = (c_uint32 * 2)(0x4D485549, 1)
        _carbon.RegisterEventHotKey(
            spaceKeyCode, optionKey,
            ctypes.cast(hkid, c_void_p),
            _carbon.GetApplicationEventTarget(), 0,
            byref(self._hkref))

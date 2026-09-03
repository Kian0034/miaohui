"""pyobjc 冻结包兼容层：PyInstaller 收不全 AppKit 常量，这里兜底。

常量值为 AppKit ABI 稳定值（与 macOS 头文件一致）。
"""
import AppKit


def _get(name: str, fallback):
    return getattr(AppKit, name, fallback)


NSBackingStoreBuffered = _get("NSBackingStoreBuffered", 2)
NSImageScaleProportionallyUpOrDown = _get(
    "NSImageScaleProportionallyUpOrDown", 3)
NSTextAlignmentRight = _get("NSTextAlignmentRight", 1)
NSVisualEffectBlendingModeBehindWindow = _get(
    "NSVisualEffectBlendingModeBehindWindow", 0)
NSVisualEffectMaterialHUDWindow = _get("NSVisualEffectMaterialHUDWindow", 13)
NSVisualEffectStateActive = _get("NSVisualEffectStateActive", 1)
NSViewHeightSizable = _get("NSViewHeightSizable", 16)
NSViewMinXMargin = _get("NSViewMinXMargin", 1)
NSViewWidthSizable = _get("NSViewWidthSizable", 2)
NSWindowStyleMaskTitled = _get("NSWindowStyleMaskTitled", 1)
NSWindowStyleMaskUtilityWindow = _get("NSWindowStyleMaskUtilityWindow", 16)
NSWindowStyleMaskNonactivatingPanel = _get(
    "NSWindowStyleMaskNonactivatingPanel", 1 << 7)
NSWindowStyleMaskFullSizeContentView = _get(
    "NSWindowStyleMaskFullSizeContentView", 1 << 8)
NSStatusItemVariableLength = _get("NSStatusItemVariableLength", -1)
NSWindowTitleHidden = _get("NSWindowTitleHidden", 1 << 11)

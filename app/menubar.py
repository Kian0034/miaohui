"""菜单栏（NSStatusItem）：状态、暂停/恢复索引、透明度审计入口、退出。"""
import objc
from AppKit import NSApp, NSImage, NSMenu, NSMenuItem, NSMenuItemSeparator, \
    NSStatusBar, NSStatusItemVariableLength
from Foundation import NSObject, NSTimer

from .. import config
from . import opener


class MenuBarController(NSObject):
    def initWithApp_(self, app):
        self = objc.super(MenuBarController, self).init()
        if self is None:
            return None
        self.app = app
        self._build()
        self._timer = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            2.0, self, "refreshStats:", None, True)
        return self

    def _build(self):
        item = NSStatusBar.systemStatusBar().statusItemWithLength_(
            NSStatusItemVariableLength)
        self.item = item
        try:
            icon = NSImage.imageWithSystemSymbolName_accessibilityDescription_(
                "text.magnifyingglass", "MiaoHui")
            if icon:
                icon.setTemplate_(True)
                item.setImage_(icon)
            else:
                item.setTitle_("⌥S")
        except Exception:
            item.setTitle_("秒")

        menu = NSMenu.alloc().initWithTitle_("MiaoHui")

        self.title_item = self._add(menu, "秒回 · 本地搜索引擎（离线）", self._noop, enabled=False)
        self.stats_item = self._add(menu, "索引统计：加载中…", self._noop, enabled=False)
        self._sep(menu)
        self._add(menu, "搜索（⌥Space）", self._search)
        self._sep(menu)
        self.toggle_item = self._add(menu, "暂停索引", self._toggle_index)
        self._add(menu, "打开索引与审计目录", self._open_support)
        self.sens_item = self._add(menu, "敏感内容保护：开启 ✓", self._toggle_sensitive)
        self._sep(menu)
        self._add(menu, "退出", self._quit)
        item.setMenu_(menu)
        self.menu = menu

    def _add(self, menu, title, action, enabled=True):
        it = NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title, None, "")
        it.setTarget_(self)
        it.setAction_(action if action != self._noop else None)
        it.setEnabled_(enabled)
        menu.addItem_(it)
        return it

    def _sep(self, menu):
        from AppKit import NSMenuItemSeparator
        menu.addItem_(NSMenuItemSeparator.separatorItem())

    def _noop(self, s):
        pass

    # ---------- actions ----------
    def _search(self, s):
        self.app.show_panel()

    def _toggle_index(self, s):
        running = self.app.toggle_indexing()
        s.setTitle_("暂停索引" if not running else "恢复索引")

    def _toggle_sensitive(self, s):
        st = config.load_settings()
        st["sensitive_protection"] = not st.get("sensitive_protection", True)
        config.save_settings(st)
        s.setTitle_("敏感内容保护：开启 ✓" if st["sensitive_protection"]
                    else "敏感内容保护：关闭 ✗")

    def _open_support(self, s):
        opener.reveal_in_finder(str(config.SUPPORT_DIR))

    def _quit(self, s):
        self.app.shutdown()
        NSApp.terminate_(None)

    # ---------- 定时刷新 ----------
    def refreshStats_(self, timer):
        st = self.app.stats()
        self.stats_item.setTitle_(
            f"已索引 {st.get('files', 0)} 文件 / {st.get('items', 0)} 项"
            f"（图片 {st.get('images', 0)} · 帧 {st.get('frames', 0)} · 语音 {st.get('asr', 0)}）")

"""Spotlight 风格搜索面板（原生 AppKit，HUD 毛玻璃，视图复用表格）。"""
import os
import threading

import objc
from AppKit import (NSBox, NSColor, NSFont, NSImage, NSImageView, NSIndexSet,
                    NSMakeRect, NSPanel, NSScreen, NSScrollView, NSTableColumn,
                    NSTableView, NSTextField, NSView, NSWindowStyleMaskTitled)
from Foundation import NSObject, NSTimer
from ._compat import (NSBackingStoreBuffered,
                      NSImageScaleProportionallyUpOrDown,
                      NSTextAlignmentRight,
                      NSVisualEffectBlendingModeBehindWindow,
                      NSVisualEffectMaterialHUDWindow,
                      NSVisualEffectStateActive, NSViewHeightSizable,
                      NSViewMinXMargin, NSViewWidthSizable,
                      NSWindowStyleMaskFullSizeContentView,
                      NSWindowStyleMaskNonactivatingPanel,
                      NSWindowStyleMaskUtilityWindow, NSWindowTitleHidden)


def _sys_font(size, semibold=False):
    try:
        return NSFont.systemFont_weight_(size, 0.3 if semibold else 0.0)
    except Exception:
        return NSFont.systemFontOfSize_(size)


def _color(r, g, b, a=1.0):
    return NSColor.colorWithSRGBRed_green_blue_alpha_(r, g, b, a)


ACCENT = _color(0.40, 0.66, 1.0)
TXT_MAIN = _color(0.96, 0.97, 1.0)
TXT_SUB = _color(0.68, 0.71, 0.78)


class ResultRowView(NSView):
    """行视图：缩略图 + 标题 + 徽章 + 路径/摘录。"""

    def initWithFrame_(self, frame):
        self = objc.super(ResultRowView, self).initWithFrame_(frame)
        if self is None:
            return None
        self.setIdentifier_("mhrow")
        self._built = False
        return self

    @objc.python_method
    def _build(self):
        if self._built:
            return
        b = self.bounds()
        h = b.size.height
        self.thumb = NSImageView.alloc().initWithFrame_(
            NSMakeRect(10, 7, 74, 50))
        self.thumb.setImageScaling_(NSImageScaleProportionallyUpOrDown)
        try:
            self.thumb.setWantsLayer_(True)
            self.thumb.layer().setCornerRadius_(6.0)
            self.thumb.layer().setMasksToBounds_(True)
        except Exception:
            pass
        self.addSubview_(self.thumb)

        self.title = NSTextField.labelWithString_("")
        self.title.setFrame_(NSMakeRect(96, h - 27, 400, 19))
        self.title.setFont_(_sys_font(14, True))
        self.title.setTextColor_(TXT_MAIN)
        self.title.setAutoresizingMask_(NSViewWidthSizable)
        self.addSubview_(self.title)

        self.badge = NSTextField.labelWithString_("")
        self.badge.setFrame_(NSMakeRect(b.size.width - 130, h - 26, 116, 18))
        self.badge.setAlignment_(NSTextAlignmentRight)
        self.badge.setFont_(_sys_font(12, True))
        self.badge.setTextColor_(ACCENT)
        self.badge.setAutoresizingMask_(NSViewMinXMargin)
        self.addSubview_(self.badge)

        self.sub = NSTextField.labelWithString_("")
        self.sub.setFrame_(NSMakeRect(96, 8, b.size.width - 112, 30))
        self.sub.setFont_(_sys_font(11))
        self.sub.setTextColor_(TXT_SUB)
        self.sub.setLineBreakMode_(2)  # 截尾
        self.sub.setMaximumNumberOfLines_(2)
        self.sub.setAutoresizingMask_(NSViewWidthSizable)
        self.addSubview_(self.sub)
        self._built = True

    def update_(self, meta):
        self._build()
        if meta.get("thumb"):
            self.thumb.setImage_(NSImage.alloc().initWithData_(meta["thumb"]))
        else:
            self.thumb.setImage_(None)
        name = os.path.basename(meta["path"]) or meta["path"]
        self.title.setStringValue_(name)
        kind = meta.get("kind")
        if kind == "frame":
            t = int(meta.get("ts") or 0)
            self.badge.setStringValue_(f"{t // 60:02d}:{t % 60:02d}")
        elif kind == "asr":
            t = int(meta.get("ts") or 0)
            self.badge.setStringValue_(f"语音 {t // 60:02d}:{t % 60:02d}")
        elif kind == "image":
            self.badge.setStringValue_("图片")
        else:
            self.badge.setStringValue_("")
        rel = os.path.dirname(meta["path"]).replace(os.path.expanduser("~"), "~")
        snippet = (meta.get("asr") or meta.get("ocr") or "").replace("\n", " ")
        sub = rel
        if snippet:
            sub += "  ·  「" + snippet[:90] + "」"
        self.sub.setStringValue_(sub)


class SearchPanel(NSObject):
    """控制器：面板 + 搜索线程调度 + 键盘交互。"""

    def initWithService_(self, service):
        self = objc.super(SearchPanel, self).init()
        if self is None:
            return None
        self.service = service
        self.on_open = None          # callable(path, ts)
        self.stats_provider = None   # callable() -> dict
        self._rows = []
        self._gen = 0
        self._debounce = None
        self._build_window()
        return self

    # ---------- UI ----------
    @objc.python_method
    def _build_window(self):
        style = (NSWindowStyleMaskNonactivatingPanel |
                 NSWindowStyleMaskTitled |
                 NSWindowStyleMaskUtilityWindow |
                 NSWindowStyleMaskFullSizeContentView)
        w, h = 720, 540
        frame = NSScreen.mainScreen().frame()
        x = frame.origin.x + (frame.size.width - w) / 2
        y = frame.origin.y + frame.size.height * 0.80 - h
        panel = NSPanel.alloc().initWithContentRect_styleMask_backing_defer_(
            NSMakeRect(x, y, w, h), style, NSBackingStoreBuffered, False)
        panel.setLevel_(3)
        panel.setTitleVisibility_(NSWindowTitleHidden)
        panel.setTitlebarAppearsTransparent_(True)
        panel.setMovableByWindowBackground_(True)
        panel.setHidesOnDeactivate_(False)
        panel.setReleasedWhenClosed_(False)
        panel.setDelegate_(self)
        self.panel = panel

        NSVisualEffectView = getattr(
            __import__("AppKit"), "NSVisualEffectView", None)
        if NSVisualEffectView is None:
            fx = None
        else:
            fx = NSVisualEffectView.alloc().initWithFrame_(
                NSMakeRect(0, 0, w, h))
            fx.setMaterial_(NSVisualEffectMaterialHUDWindow)
            fx.setBlendingMode_(NSVisualEffectBlendingModeBehindWindow)
            fx.setState_(NSVisualEffectStateActive)
            fx.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
            panel.contentView().addSubview_(fx)
        self.fx = fx

        self.field = NSTextField.alloc().initWithFrame_(
            NSMakeRect(22, h - 66, w - 44, 36))
        self.field.setBezeled_(False)
        self.field.setFocusRingType_(2)  # none
        self.field.setDrawsBackground_(False)
        self.field.setEditable_(True)
        self.field.setPlaceholderString_("搜索这台电脑上的一切… ⌥Space 随时唤起")
        self.field.setFont_(_sys_font(22))
        self.field.setTextColor_(TXT_MAIN)
        self.field.setDelegate_(self)
        fx.addSubview_(self.field)

        line = NSBox.alloc().initWithFrame_(NSMakeRect(22, h - 76, w - 44, 1))
        line.setBoxType_(2)  # 分隔线
        line.setAutoresizingMask_(NSViewWidthSizable)
        fx.addSubview_(line)

        self.table = NSTableView.alloc().initWithFrame_(
            NSMakeRect(0, 0, w, h - 120))
        col = NSTableColumn.alloc().initWithIdentifier_("main")
        self.table.addTableColumn_(col)
        self.table.setHeaderView_(None)
        self.table.setRowHeight_(64)
        self.table.setDelegate_(self)
        self.table.setDataSource_(self)
        self.table.setSelectionHighlightStyle_(0)
        self.table.setBackgroundColor_(NSColor.clearColor())
        self.table.setAllowsEmptySelection_(True)

        scroll = NSScrollView.alloc().initWithFrame_(
            NSMakeRect(0, 42, w, h - 122))
        scroll.setDocumentView_(self.table)
        scroll.setHasVerticalScroller_(True)
        scroll.setDrawsBackground_(False)
        scroll.setAutohidesScrollers_(True)
        scroll.setAutoresizingMask_(NSViewWidthSizable | NSViewHeightSizable)
        fx.addSubview_(scroll)

        self.footer = NSTextField.labelWithString_("")
        self.footer.setFrame_(NSMakeRect(22, 14, w - 44, 18))
        self.footer.setFont_(_sys_font(11))
        self.footer.setTextColor_(TXT_SUB)
        self.footer.setAutoresizingMask_(NSViewWidthSizable)
        fx.addSubview_(self.footer)

    # ---------- 显示/隐藏 ----------
    def toggle(self):
        if self.panel.isVisible():
            self.hide()
        else:
            self.show()

    def show(self):
        self.panel.makeKeyAndOrderFront_(None)
        import AppKit
        NSApp = getattr(AppKit, "NSApp", None)
        if NSApp is not None:
            NSApp.activateIgnoringOtherApps_(True)
        self.panel.makeFirstResponder_(self.field)
        st = self.stats_provider() if self.stats_provider else {}
        self.footer.setStringValue_(
            f"全程离线 · 已索引 {st.get('files', 0)} 文件 / {st.get('items', 0)} 项"
            f" · 敏感内容已排除 {st.get('skipped', 0)}")

    def hide(self):
        self.panel.orderOut_(None)

    def windowDidResignKey_(self, note):
        self.hide()

    # ---------- 输入 ----------
    def controlTextDidChange_(self, note):
        if self._debounce:
            self._debounce.invalidate()
        self._debounce = NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            0.12, self, "doSearch:", None, False)

    def control_textView_doCommandBySelector_(self, ctrl, tv, sel):
        s = str(sel)
        if s == "cancelOperation:":          # Esc
            self.hide()
            return True
        if s == "moveUp:":                   # ↑
            n = self.table.numberOfRows()
            if n:
                cur = self.table.selectedRow()
                self.table.selectRowIndexes_byExtendingSelection_(
                    NSIndexSet.indexSetWithIndex_(max(0, cur - 1)), False)
                self.table.scrollRowToVisible_(max(0, cur - 1))
            return True
        if s == "moveDown:":                 # ↓
            n = self.table.numberOfRows()
            if n:
                cur = self.table.selectedRow()
                nxt = min(n - 1, cur + 1)
                self.table.selectRowIndexes_byExtendingSelection_(
                    NSIndexSet.indexSetWithIndex_(nxt), False)
                self.table.scrollRowToVisible_(nxt)
            return True
        if s == "insertNewline:":            # Enter
            self.openSelected()
            return True
        return False

    # ---------- 搜索（后台线程，主线程回填） ----------
    def doSearch_(self, timer):
        q = str(self.field.stringValue()).strip()
        self._gen += 1
        gen = self._gen
        if not q:
            self._rows = []
            self.table.reloadData()
            return

        def worker():
            try:
                res = self.service.search(q, limit=30)
            except Exception as e:
                res = {"results": [], "latency_ms": -1, "error": str(e)}
            self.performSelectorOnMainThread_withObject_waitUntilDone_(
                "_applyResults:", (gen, res), False)

        threading.Thread(target=worker, daemon=True).start()

    def _applyResults_(self, payload):
        gen, res = payload
        if gen != self._gen:
            return
        self._rows = res.get("results", [])
        self.table.reloadData()
        if self._rows:
            self.table.selectRowIndexes_byExtendingSelection_(
                NSIndexSet.indexSetWithIndex_(0), False)
            self.table.scrollRowToVisible_(0)
        lat = res.get("latency_ms", -1)
        if lat >= 0:
            self.footer.setStringValue_(
                f"共 {len(self._rows)} 条结果 · {lat / 1000:.2f} 秒 · 全程离线")
        else:
            self.footer.setStringValue_("搜索出错：" + res.get("error", ""))

    # ---------- 表格 ----------
    def numberOfRowsInTableView_(self, tv):
        return len(self._rows)

    def tableView_viewForTableColumn_row_(self, tv, col, row):
        v = tv.makeViewWithIdentifier_owner_("mhrow", self)
        if v is None:
            v = ResultRowView.alloc().initWithFrame_(
                NSMakeRect(0, 0, self.table.bounds().size.width, 64))
        v.update_(self._rows[row])
        return v

    def tableView_heightOfRow_(self, tv, row):
        return 64

    def tableView_shouldSelectRow_(self, tv, row):
        return True

    def tableViewSelectionDidChange_(self, note):
        pass

    # ---------- 打开 ----------
    def openSelected(self):
        r = self.table.selectedRow()
        if 0 <= r < len(self._rows):
            m = self._rows[r]
            if self.on_open:
                self.on_open(m["path"], m.get("ts"))

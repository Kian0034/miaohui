"""Windows 托盘图标 + 菜单（索引状态 / 暂停恢复 / 退出）。"""
from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QApplication, QMenu, QSystemTrayIcon


def _app_icon() -> QIcon:
    """生成简单的“秒”字徽标托盘图标。"""
    pm = QPixmap(64, 64)
    pm.fill(QColor(0, 0, 0, 0))
    p = QPainter(pm)
    p.setRenderHint(QPainter.Antialiasing)
    p.setBrush(QColor("#121820"))
    p.setPen(QColor("#66A8FF"), 3)
    p.drawRoundedRect(3, 3, 58, 58, 14, 14)
    p.setPen(QColor("#66A8FF"))
    f = p.font()
    f.setPixelSize(30)
    f.setBold(True)
    p.setFont(f)
    p.drawText(pm.rect(), 0x0084 | 0x0001, "秒")  # center
    p.end()
    return QIcon(pm)


class TrayController:
    def __init__(self, app):
        self.app = app
        self.tray = QSystemTrayIcon(_app_icon())
        self.menu = QMenu()

        self.act_search = QAction("立即搜索 (Ctrl+Alt+Space)")
        self.act_search.triggered.connect(lambda: app.show_panel())
        self.menu.addAction(self.act_search)

        self.menu.addSeparator()

        self.act_toggle = QAction("暂停索引")
        self.act_toggle.triggered.connect(self._toggle_index)
        self.menu.addAction(self.act_toggle)

        self.menu.addSeparator()

        act_quit = QAction("退出")
        act_quit.triggered.connect(self._quit)
        self.menu.addAction(act_quit)

        self.tray.setContextMenu(self.menu)
        self.tray.setToolTip("秒回 MiaoHui · 纯本地搜索")
        self.tray.show()
        self._timer = None
        self._refresh()

    def _toggle_index(self):
        running = self.app.toggle_indexing()
        self.act_toggle.setText("暂停索引" if running else "恢复索引")

    def _refresh(self):
        try:
            s = self.app.stats() or {}
            self.tray.setToolTip(
                f"秒回 MiaoHui · 已索引 {s.get('items', 0)} 项 · 纯本地")
        except Exception:
            pass
        from PySide6.QtCore import QTimer
        self._timer = QTimer()
        self._timer.setInterval(4000)
        self._timer.timeout.connect(self._refresh_stats_only)
        self._timer.start()

    def _refresh_stats_only(self):
        try:
            s = self.app.stats() or {}
            self.tray.setToolTip(
                f"秒回 MiaoHui · 已索引 {s.get('items', 0)} 项 · 纯本地")
        except Exception:
            pass

    def _quit(self):
        self.app.shutdown()
        self.tray.hide()
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

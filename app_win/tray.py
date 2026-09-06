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

        act_stop = QAction("停止索引并释放资源")
        act_stop.triggered.connect(self._stop_index)
        self.menu.addAction(act_stop)

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
        if self.app.indexing_running():
            paused = self.app.is_paused()
            self.app.set_paused(not paused)
            self.act_toggle.setText("恢复索引" if not paused else "暂停索引")
        else:
            self.app.set_paused(False)
            self.act_toggle.setText("暂停索引")

    def _stop_index(self):
        """彻底停止索引进程树（含 ffmpeg），释放全部资源。"""
        self.app.stop_indexing()
        self.app._set_pause_flag(False)
        self.act_toggle.setText("启动索引")

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

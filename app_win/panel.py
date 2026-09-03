"""Spotlight 风格搜索面板（PySide6，深色毛玻璃风，视图复用列表）。"""
import os

from PySide6.QtCore import Qt, QThreadPool, QTimer, QEvent, Signal
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtWidgets import (QFrame, QHBoxLayout, QLabel, QLineEdit,
                               QListWidget, QListWidgetItem, QMainWindow,
                               QVBoxLayout, QWidget)

ACCENT = "#66A8FF"
TXT_MAIN = "#F5F7FF"
TXT_SUB = "#ADB3BF"
BG = "rgba(18,22,30,0.96)"


class ResultItem(QWidget):
    """行视图：缩略图 + 标题 + 徽章 + 路径/摘录。"""

    def __init__(self, meta: dict, parent=None):
        super().__init__(parent)
        self.meta = meta
        lay = QHBoxLayout(self)
        lay.setContentsMargins(10, 7, 12, 7)
        lay.setSpacing(12)

        self.thumb = QLabel()
        self.thumb.setFixedSize(74, 50)
        self.thumb.setAlignment(Qt.AlignCenter)
        self.thumb.setStyleSheet(
            "background:#232a36;border-radius:6px;")
        lay.addWidget(self.thumb)

        mid = QVBoxLayout()
        mid.setSpacing(3)
        self.title = QLabel(self._name())
        f = QFont("Microsoft YaHei UI", 10)
        f.setBold(True)
        self.title.setFont(f)
        self.title.setStyleSheet(f"color:{TXT_MAIN};")
        self.sub = QLabel(self._sub())
        self.sub.setFont(QFont("Microsoft YaHei UI", 8))
        self.sub.setStyleSheet(f"color:{TXT_SUB};")
        self.sub.setMaximumWidth(560)
        mid.addWidget(self.title)
        mid.addWidget(self.sub)
        lay.addLayout(mid, 1)

        self.badge = QLabel(self._badge())
        bf = QFont("Microsoft YaHei UI", 8)
        bf.setBold(True)
        self.badge.setFont(bf)
        self.badge.setStyleSheet(f"color:{ACCENT};")
        self.badge.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        lay.addWidget(self.badge)

        pm = meta.get("thumb")
        if pm:
            pix = QPixmap()
            if pix.loadFromData(pm):
                self.thumb.setPixmap(pix.scaled(
                    74, 50, Qt.KeepAspectRatioByExpanding,
                    Qt.SmoothTransformation))

    def _name(self):
        return os.path.basename(self.meta["path"]) or self.meta["path"]

    def _badge(self):
        kind = self.meta.get("kind")
        if kind == "frame":
            t = int(self.meta.get("ts") or 0)
            return f"视频 {t // 60}:{t % 60:02d}"
        if kind == "image":
            return "图片"
        if kind == "audio":
            return "音频"
        return "文档"

    def _sub(self):
        m = self.meta
        parts = []
        if m.get("ocr"):
            parts.append("OCR: " + m["ocr"].replace("\n", " ")[:60])
        if m.get("asr"):
            parts.append("ASR: " + m["asr"].replace("\n", " ")[:60])
        parts.append(m["path"])
        return "  ·  ".join(parts)


class SearchPanel(QMainWindow):
    """无边框置顶面板：顶部搜索框 + 结果列表 + 底部状态。"""

    open_requested = Signal(str, object)

    def __init__(self, service, stats_provider=None, parent=None):
        super().__init__(parent)
        self.service = service
        self.stats_provider = stats_provider
        self.on_open = None
        self._results = []
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(120)
        self._debounce.timeout.connect(self._do_search)

        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Tool |
                            Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(760, 520)

        shell = QFrame(self)
        shell.setGeometry(0, 0, 760, 520)
        shell.setStyleSheet(
            f"QFrame{{background:{BG};border:1px solid #2A3242;"
            f"border-radius:14px;}}")
        root = QVBoxLayout(shell)
        root.setContentsMargins(18, 16, 18, 10)
        root.setSpacing(10)

        self.input = QLineEdit()
        self.input.setPlaceholderText(
            "搜索照片、截图、视频帧、文件内容…（Ctrl+Alt+Space 呼出）")
        self.input.setFont(QFont("Microsoft YaHei UI", 13))
        self.input.setFixedHeight(44)
        self.input.setStyleSheet(
            "QLineEdit{background:#1B212C;border:1px solid #2A3242;"
            "border-radius:10px;padding:0 14px;color:" + TXT_MAIN + ";}"
            f"QLineEdit:focus{{border:1px solid {ACCENT};}}")
        self.input.textChanged.connect(lambda _: self._debounce.start())
        self.input.installEventFilter(self)
        root.addWidget(self.input)

        self.list = QListWidget()
        self.list.setStyleSheet(
            "QListWidget{background:transparent;border:none;}"
            "QListWidget::item{border-radius:8px;}"
            f"QListWidget::item:selected{{background:#24304A;}}")
        self.list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.list.setSelectionMode(QListWidget.SingleSelection)
        self.list.itemClicked.connect(lambda _: self._open_current())
        root.addWidget(self.list, 1)

        self.status = QLabel("秒回 MiaoHui · 纯本地检索")
        self.status.setFont(QFont("Microsoft YaHei UI", 8))
        self.status.setStyleSheet(f"color:{TXT_SUB};")
        root.addWidget(self.status)

    # ---------- 显示 / 隐藏 ----------
    def show(self):  # noqa: A003
        super().show()
        self._center()
        self.input.setFocus()
        self.input.selectAll()
        self._refresh_stats()

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show()

    def _center(self):
        screen = self.screen() or self.windowHandle().screen()
        g = screen.availableGeometry()
        self.move(g.center().x() - self.width() // 2,
                  g.top() + int(g.height() * 0.18))

    # ---------- 检索 ----------
    def _do_search(self):
        q = self.input.text().strip()
        if not q:
            self.list.clear()
            self._results = []
            self._refresh_stats()
            return

        def job():
            try:
                res = self.service.search(q)
            except Exception:
                res = {"results": [], "latency_ms": -1}
            QTimer.singleShot(0, lambda: self._apply(res))

        QThreadPool.globalInstance().start(job)

    def _apply(self, res):
        self._results = res["results"]
        self.list.clear()
        for meta in self._results:
            it = QListWidgetItem(self.list)
            it.setSizeHint(ResultItem(meta).sizeHint())
            w = ResultItem(meta, self.list)
            it.setSizeHint(w.sizeHint())
            self.list.setItemWidget(it, w)
        lat = res.get("latency_ms", -1)
        self.status.setText(
            f"{len(self._results)} 个结果 · {lat:.0f} ms · 全部在本机"
            if lat >= 0 else "检索出错")
        if self._results:
            self.list.setCurrentRow(0)

    def _refresh_stats(self):
        if not self.stats_provider:
            return
        try:
            s = self.stats_provider() or {}
            self.status.setText(
                f"已索引 {s.get('items', 0)} 项 · 视觉向量 {s.get('vis', 0)}"
                f" · 文本向量 {s.get('txt', 0)} · 纯本地")
        except Exception:
            pass

    # ---------- 键盘 ----------
    def eventFilter(self, obj, ev):
        from PySide6.QtCore import QEvent
        if obj is self.input and ev.type() == QEvent.KeyPress:
            key = ev.key()
            if key == Qt.Key_Escape:
                self.hide()
                return True
            if key in (Qt.Key_Return, Qt.Key_Enter):
                self._open_current()
                return True
            if key == Qt.Key_Down:
                r = self.list.currentRow()
                self.list.setCurrentRow(min(r + 1, self.list.count() - 1))
                return True
            if key == Qt.Key_Up:
                r = self.list.currentRow()
                self.list.setCurrentRow(max(r - 1, 0))
                return True
        return super().eventFilter(obj, ev)

    def _open_current(self):
        it = self.list.currentItem()
        if not it or not self.on_open:
            return
        meta = self._results[self.list.row(it)]
        self.hide()
        self.on_open(meta["path"], meta.get("ts"))

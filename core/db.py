"""SQLite 元数据库 + FTS5 中文全文索引 + HNSW 向量索引管理。

表结构：
  files  — 源文件（增量索引依据：mtime+size）
  items  — 可检索单元：整图 / 视频帧 / 语音段落
  texts  — FTS5 外部内容表（jieba 预分词）
向量：hnswlib 双索引（视觉 512 / 文本 384），label == item.id
"""
import json
import sqlite3
import threading
import time
from pathlib import Path

from . import config
from .config import DIM_TXT, DIM_VIS

_SCHEMA = """
PRAGMA journal_mode=WAL;
CREATE TABLE IF NOT EXISTS files(
  id INTEGER PRIMARY KEY,
  path TEXT UNIQUE NOT NULL,
  kind TEXT NOT NULL,          -- image | video
  mtime REAL NOT NULL,
  size INTEGER NOT NULL,
  duration REAL,               -- 视频时长
  n_items INTEGER DEFAULT 0,
  indexed_at REAL,
  status TEXT DEFAULT 'ok'     -- ok | skipped_sensitive | error
);
CREATE INDEX IF NOT EXISTS idx_files_path ON files(path);

CREATE TABLE IF NOT EXISTS items(
  id INTEGER PRIMARY KEY,
  file_id INTEGER NOT NULL REFERENCES files(id) ON DELETE CASCADE,
  kind TEXT NOT NULL,          -- image | frame | asr
  ts REAL,                     -- 视频内时间点（秒）
  dur REAL,                    -- 段落时长（asr）
  ocr TEXT DEFAULT '',         -- OCR 文本（图像/帧）
  asr TEXT DEFAULT '',         -- ASR 文本（语音段落）
  thumb BLOB                   -- 加密缩略图
);
CREATE INDEX IF NOT EXISTS idx_items_file ON items(file_id);

CREATE VIRTUAL TABLE IF NOT EXISTS texts USING fts5(
  body, item_id UNINDEXED
);
"""


class DB:
    def __init__(self, path: Path = None):
        config.ensure_dirs()
        self.path = Path(path) if path else config.DB_PATH
        self._lock = threading.Lock()
        self.conn = sqlite3.connect(str(self.path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA synchronous=NORMAL")
        self.conn.executescript(_SCHEMA)
        self.conn.commit()

    # ---------- files ----------
    def upsert_file(self, path: str, kind: str, mtime: float, size: int,
                    duration: float = None, status: str = "ok") -> int:
        with self._lock, self.conn:
            cur = self.conn.execute(
                """INSERT INTO files(path,kind,mtime,size,duration,status,indexed_at)
                   VALUES(?,?,?,?,?,?,?)
                   ON CONFLICT(path) DO UPDATE SET
                     kind=excluded.kind, mtime=excluded.mtime, size=excluded.size,
                     duration=excluded.duration, status=excluded.status,
                     indexed_at=excluded.indexed_at""",
                (path, kind, mtime, size, duration, status, time.time()),
            )
            row = self.conn.execute(
                "SELECT id FROM files WHERE path=?", (path,)
            ).fetchone()
            fid = row["id"]
            if kind == "video" and status == "ok":
                # 重建视频条目：先清旧帧
                self.conn.execute(
                    "DELETE FROM items WHERE file_id=?", (fid,))
                self.conn.execute(
                    "DELETE FROM texts WHERE item_id IN (SELECT id FROM items WHERE file_id=?)",
                    (fid,))
            return fid

    def find_file(self, path: str):
        return self.conn.execute(
            "SELECT * FROM files WHERE path=?", (path,)).fetchone()

    def unchanged(self, path: str, mtime: float, size: int) -> bool:
        r = self.find_file(path)
        return bool(r and r["status"] == "ok"
                    and abs(r["mtime"] - mtime) < 1e-6 and r["size"] == size)

    # ---------- items ----------
    def add_item(self, file_id: int, kind: str, ts, dur, ocr: str, asr: str,
                 thumb: bytes) -> int:
        with self._lock, self.conn:
            cur = self.conn.execute(
                """INSERT INTO items(file_id,kind,ts,dur,ocr,asr,thumb)
                   VALUES(?,?,?,?,?,?,?)""",
                (file_id, kind, ts, dur, ocr, asr, thumb),
            )
            iid = cur.lastrowid
            body = " ".join(filter(None, [ocr, asr]))
            if body:
                self.conn.execute(
                    "INSERT INTO texts(body,item_id) VALUES(?,?)",
                    (_tokenize(body), iid),
                )
            return iid

    def bump_item_count(self, file_id: int, n: int):
        with self._lock, self.conn:
            self.conn.execute(
                "UPDATE files SET n_items=? WHERE id=?", (n, file_id))

    def item_meta(self, item_ids: list) -> list:
        if not item_ids:
            return []
        q = ",".join("?" * len(item_ids))
        rows = self.conn.execute(
            f"""SELECT i.id, i.kind, i.ts, i.dur, i.ocr, i.asr, i.thumb,
                       f.path, f.kind AS fkind, f.duration AS fdur
                FROM items i JOIN files f ON f.id=i.file_id
                WHERE i.id IN ({q})""",
            item_ids,
        ).fetchall()
        by_id = {r["id"]: dict(r) for r in rows}
        return [by_id[i] for i in item_ids if i in by_id]

    # ---------- FTS ----------
    def fts_search(self, tokens: str, k: int = 64) -> list:
        """tokens: jieba 分词后空格连接的查询串。返回 [item_id]（按 bm25 升序）"""
        try:
            rows = self.conn.execute(
                """SELECT item_id, bm25(texts) AS rank FROM texts
                   WHERE texts MATCH ? ORDER BY rank LIMIT ?""",
                (tokens, k),
            ).fetchall()
            return [int(r["item_id"]) for r in rows]
        except sqlite3.OperationalError:
            return []

    # ---------- 统计 ----------
    def stats(self) -> dict:
        c = self.conn
        n_files = c.execute("SELECT COUNT(*) n FROM files").fetchone()["n"]
        n_items = c.execute("SELECT COUNT(*) n FROM items").fetchone()["n"]
        n_img = c.execute(
            "SELECT COUNT(*) n FROM items WHERE kind='image'").fetchone()["n"]
        n_frame = c.execute(
            "SELECT COUNT(*) n FROM items WHERE kind='frame'").fetchone()["n"]
        n_asr = c.execute(
            "SELECT COUNT(*) n FROM items WHERE kind='asr'").fetchone()["n"]
        n_skip = c.execute(
            "SELECT COUNT(*) n FROM files WHERE status='skipped_sensitive'"
        ).fetchone()["n"]
        return dict(files=n_files, items=n_items, images=n_img,
                    frames=n_frame, asr=n_asr, skipped=n_skip)


# ---------- jieba 中文分词（索引与查询共用） ----------
_jieba = None


def _jieba_cut(s: str) -> list:
    global _jieba
    if _jieba is None:
        import jieba
        jieba.setLogLevel(60)
        _jieba = jieba
    return list(_jieba.cut(s))


def _tokenize(text: str) -> str:
    toks = [t.strip() for t in _jieba_cut(text) if t.strip()]
    return " ".join(toks) if toks else text


def tokenize_query(text: str) -> str:
    toks = [t.strip() for t in _jieba_cut(text) if t.strip()]
    # 既有整句又有分词，兼顾精确短语与词命中
    parts = [f'"{text}"'] if text.strip() else []
    parts += [f'"{t}"' for t in toks if len(t) >= 2]
    seen, out = set(), []
    for p in parts:
        if p not in seen:
            seen.add(p)
            out.append(p)
    return " OR ".join(out) if out else text


# ---------- HNSW 管理 ----------
class HNSW:
    """hnswlib 封装：自动扩容、持久化。label = item.id"""

    def __init__(self, path: Path, dim: int):
        import hnswlib
        self.path = Path(path)
        self.dim = dim
        self._lib = hnswlib
        if self.path.exists():
            self.index = hnswlib.Index(space="cosine", dim=dim)
            self.index.load_index(str(self.path))
        else:
            self.index = hnswlib.Index(space="cosine", dim=dim)
            self.index.init_index(max_elements=1024, ef_construction=200,
                                  M=16)
        self.index.set_ef(64)

    @property
    def count(self) -> int:
        return int(self.index.element_count)

    def add(self, vectors, labels):
        if len(vectors) == 0:
            return
        if self.index.element_count + len(vectors) > self.index.max_elements:
            self.index.resize_index(
                max(self.index.max_elements * 2,
                    self.index.element_count + len(vectors) + 1024))
        self.index.add_items(vectors, labels)

    def knn(self, q, k: int = 64):
        n = self.index.element_count
        if n == 0:
            return []
        labels, _ = self.index.knn_query(q, k=min(k, n))
        return [int(l) for l in labels[0]]

    def save(self):
        tmp = str(self.path) + ".tmp"
        self.index.save_index(tmp)
        Path(tmp).replace(self.path)

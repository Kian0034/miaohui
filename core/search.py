"""检索服务：三路召回融合（视觉向量 / 文本向量 / FTS 全文），RRF 排序。

0.3 秒目标：CLIP 文本编码 ~15ms + bge ~10ms + HNSW <5ms + FTS <10ms + 取行 <10ms
"""
import time
from pathlib import Path

from . import config
from .db import DB, HNSW, tokenize_query


class SearchResult(dict):
    @property
    def path(self): return self["path"]


class SearchService:
    def __init__(self):
        self.db = DB()
        self.vis = HNSW(config.HNSW_VIS_PATH, config.DIM_VIS)
        self.txt = HNSW(config.HNSW_TXT_PATH, config.DIM_TXT)
        self.vis_mtime = self._mtime(config.HNSW_VIS_PATH)
        self.txt_mtime = self._mtime(config.HNSW_TXT_PATH)
        self._models = None

    @staticmethod
    def _mtime(p: Path):
        try:
            return p.stat().st_mtime
        except OSError:
            return 0

    def _maybe_reload(self):
        """索引进程落盘后热加载（限频 5s）。"""
        now = time.time()
        if now - getattr(self, "_last_check", 0) < 5:
            return
        self._last_check = now
        m1 = self._mtime(config.HNSW_VIS_PATH)
        if m1 != self.vis_mtime:
            try:
                self.vis = HNSW(config.HNSW_VIS_PATH, config.DIM_VIS)
                self.vis_mtime = m1
            except Exception:
                pass
        m2 = self._mtime(config.HNSW_TXT_PATH)
        if m2 != self.txt_mtime:
            try:
                self.txt = HNSW(config.HNSW_TXT_PATH, config.DIM_TXT)
                self.txt_mtime = m2
            except Exception:
                pass

    def _models_load(self):
        if self._models is None:
            from . import embed
            self._models = (embed.clip(), embed.bge())
        return self._models

    def search(self, query: str, limit: int = 30) -> dict:
        """返回 {results, latency_ms, breakdown}"""
        t0 = time.perf_counter()
        self._maybe_reload()
        clip, bge = self._models_load()
        bk = {}

        # 1) 视觉语义（CLIP 文本塔 ↔ 图/帧）
        t1 = time.perf_counter()
        qv = clip.encode_text(query)
        vis_hits = self.vis.knn(qv, k=64)
        bk["clip"] = round((time.perf_counter() - t1) * 1000, 1)

        # 2) 文本语义（bge ↔ ASR 语音段落 + OCR 段落）
        t2 = time.perf_counter()
        qt = bge.encode(query)
        txt_hits = self.txt.knn(qt, k=64)
        bk["bge"] = round((time.perf_counter() - t2) * 1000, 1)

        # 3) 关键词全文（jieba + FTS5）
        t3 = time.perf_counter()
        fts_hits = self.db.fts_search(tokenize_query(query), k=64)
        bk["fts"] = round((time.perf_counter() - t3) * 1000, 1)

        # ---- RRF 融合 ----
        # FTS 是用户明确关键词的精确命中，权重最高；CLIP/bge 为语义近邻。
        t4 = time.perf_counter()
        weights = (1.0, 1.0, 3.0)  # vis / txt / fts
        scores: dict = {}
        for w, hits in zip(weights, (vis_hits, txt_hits, fts_hits)):
            for rank, iid in enumerate(hits):
                scores[iid] = scores.get(iid, 0.0) + w / (60 + rank)
        top = sorted(scores.items(), key=lambda kv: -kv[1])[:limit]
        bk["fuse"] = round((time.perf_counter() - t4) * 1000, 1)

        # 4) 取行 + 解密缩略图
        t5 = time.perf_counter()
        metas = self.db.item_meta([i for i, _ in top])
        from . import security
        results = []
        for iid, sc in top:
            m = next((x for x in metas if x["id"] == iid), None)
            if not m:
                continue
            thumb = None
            if m.get("thumb"):
                try:
                    thumb = security.dec(m["thumb"])
                except Exception:
                    thumb = None
            results.append(SearchResult(
                id=iid, score=round(sc, 4), path=m["path"],
                kind=m["kind"], fkind=m["fkind"], ts=m["ts"], dur=m["dur"],
                ocr=(m["ocr"] or "")[:160], asr=(m["asr"] or "")[:160],
                thumb=thumb,
            ))
        bk["fetch"] = round((time.perf_counter() - t5) * 1000, 1)

        total = round((time.perf_counter() - t0) * 1000, 1)
        return {"results": results, "latency_ms": total, "breakdown": bk,
                "index_size": self.vis.count + self.txt.count}

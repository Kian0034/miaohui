"""索引管线（独立进程跑，避免阻塞 UI）。

进程模型：
  python -m core.pipeline   → 子进程：扫描 + OCR + 嵌入 + ASR，直写 SQLite WAL，
                              HNSW 定期落盘（搜索进程按 mtime 热加载）
进度写 pipeline_state.json 供 UI 读取。
"""
import json
import os
import signal
import sys
import time
from pathlib import Path

from . import config
from .db import DB, HNSW

_state_path = config.SUPPORT_DIR / "pipeline_state.json"
_stop = False


def _write_state(**kw):
    try:
        st = {"ts": time.time()}
        st.update(kw)
        tmp = _state_path.with_suffix(".tmp")
        tmp.write_text(json.dumps(st, ensure_ascii=False), encoding="utf-8")
        tmp.replace(_state_path)
    except Exception:
        pass


def read_state() -> dict:
    try:
        return json.loads(_state_path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _sigterm(_a, _b):
    global _stop
    _stop = True


def _process_image(db: DB, clip, bge, ocr_fn, p: Path):
    """→ (item_id, vis_vec, txt_vec|None)；(None, None, None) 表示跳过。"""
    from PIL import Image
    from .frames import thumb_jpeg
    from . import security

    st = p.stat()
    if db.unchanged(str(p), st.st_mtime, st.st_size):
        return None, None, None
    im = Image.open(p)
    im.load()
    if im.width < 24 or im.height < 24:
        db.upsert_file(str(p), "image", st.st_mtime, st.st_size, status="error")
        return None, None, None
    # GIF 取第一帧
    if getattr(im, "n_frames", 1) > 1:
        im.seek(0)
    rgb = im.convert("RGB")
    thumb = thumb_jpeg(rgb)
    ocr_text = ocr_fn(rgb) if config.load_settings().get("ocr_enabled", True) else ""
    vec = clip.encode_image(rgb)
    # OCR 文本同时入语义通道（bge ~6ms），截图语义检索命中率大幅提升
    tvec = None
    if ocr_text:
        try:
            tvec = bge.encode(ocr_text[:256])
        except Exception:
            tvec = None
    fid = db.upsert_file(str(p), "image", st.st_mtime, st.st_size)
    iid = db.add_item(fid, "image", None, None, ocr_text, "",
                      security.enc(thumb))
    db.bump_item_count(fid, 1)
    return iid, vec, tvec


def _process_video(db: DB, clip, bge, ocr_fn, asr_on: bool, p: Path) -> list:
    """返回新增 item id 列表（供 HNSW 批量加入）。"""
    from . import asr as asr_mod
    from . import frames as frames_mod
    from . import security

    st = p.stat()
    if db.unchanged(str(p), st.st_mtime, st.st_size):
        return []

    dur, has_v, has_a = frames_mod.probe(str(p))
    fid = db.upsert_file(str(p), "video", st.st_mtime, st.st_size,
                         duration=dur)
    new_ids = []

    # ---- 视觉通道：帧 ----
    n_frames = 0
    if has_v:
        for t, im in frames_mod.sample_frames(str(p)):
            if _stop:
                break
            thumb = frames_mod.thumb_jpeg(im)
            ocr_text = ocr_fn(im)
            try:
                vec = clip.encode_image(im)
                iid = db.add_item(fid, "frame", t, None, ocr_text, "",
                                  security.enc(thumb))
                new_ids.append((iid, "vis", vec))
                n_frames += 1
                # 帧的 OCR 文本同样进语义通道（与图片一致）
                if ocr_text:
                    try:
                        new_ids.append((iid, "txt", bge.encode(ocr_text[:256])))
                    except Exception:
                        pass
            except Exception:
                pass

    # ---- 语音通道：ASR ----
    if asr_on and has_a and not _stop:
        try:
            pcm = frames_mod.extract_audio(str(p))
            if pcm is not None:
                for start, end, text in asr_mod.transcribe(pcm):
                    try:
                        tvec = bge.encode(text)
                        iid = db.add_item(fid, "asr", start, end - start,
                                          "", text, None)
                        new_ids.append((iid, "txt", tvec))
                    except Exception:
                        pass
        except Exception:
            pass

    db.bump_item_count(fid, len(new_ids))
    return new_ids


def run(asr: bool = None, rescan: bool = False, max_files: int = None):
    """主入口：全量增量索引。"""
    global _stop
    signal.signal(signal.SIGTERM, _sigterm)
    signal.signal(signal.SIGINT, _sigterm)

    config.ensure_dirs()
    settings = config.load_settings()
    if asr is None:
        asr = settings.get("asr_enabled", True)
    sensitive = settings.get("sensitive_protection", True)
    roots = config.expand_roots(settings)

    db = DB()
    from . import embed
    from .ocr import ocr_from_pil
    clip = embed.clip()
    bge = embed.bge()

    hnsw_vis = HNSW(config.HNSW_VIS_PATH, config.DIM_VIS)
    hnsw_txt = HNSW(config.HNSW_TXT_PATH, config.DIM_TXT)

    def flush_vecs(buf):
        vis_b, txt_b = [], []
        for iid, space, vec in buf:
            (vis_b if space == "vis" else txt_b).append((iid, vec))
        if vis_b:
            hnsw_vis.add([v for _, v in vis_b], [i for i, _ in vis_b])
        if txt_b:
            hnsw_txt.add([v for _, v in txt_b], [i for i, _ in txt_b])
        buf.clear()

    # 扫描
    _write_state(phase="scan", done=0, total=0)
    todo = []
    seen = set()
    for p in _scan_iter(sensitive):
        if _stop:
            break
        seen.add(str(p))
        todo.append(p)
    total = len(todo)
    _write_state(phase="index", done=0, total=total)
    print(f"[pipeline] scan done: {total} files", flush=True)

    vec_buf = []
    done = err = 0
    last_flush = time.time()
    t0 = time.time()

    for p in todo:
        if _stop:
            break
        if max_files and done >= max_files:
            break
        ext = p.suffix.lower()
        try:
            if ext in config.IMAGE_EXTS:
                iid, vec, tvec = _process_image(db, clip, bge,
                                                ocr_from_pil, p)
                if iid:
                    vec_buf.append((iid, "vis", vec))
                    if tvec is not None:
                        vec_buf.append((iid, "txt", tvec))
            else:
                ids = _process_video(db, clip, bge, ocr_from_pil, asr, p)
                vec_buf.extend(ids)
            done += 1
        except Exception:
            err += 1
            try:
                db.upsert_file(str(p), "video" if ext in config.VIDEO_EXTS
                               else "image", 0, 0, status="error")
            except Exception:
                pass
        if done % 25 == 0 or time.time() - last_flush > 8:
            flush_vecs(vec_buf)
            hnsw_vis.save()
            hnsw_txt.save()
            last_flush = time.time()
            _write_state(phase="index", done=done, total=total,
                         errors=err, vis=hnsw_vis.count, txt=hnsw_txt.count,
                         elapsed=round(time.time() - t0, 1))
    flush_vecs(vec_buf)
    hnsw_vis.save()
    hnsw_txt.save()
    _write_state(phase="done", done=done, total=total, errors=err,
                 vis=hnsw_vis.count, txt=hnsw_txt.count,
                 elapsed=round(time.time() - t0, 1))
    print(f"[pipeline] finished: {done}/{total} err={err}", flush=True)


def _scan_iter(sensitive: bool):
    from .scanner import scan
    settings = config.load_settings()
    roots = config.expand_roots(settings)
    return scan(roots, sensitive)


if __name__ == "__main__":
    asr_arg = None
    if "--no-asr" in sys.argv:
        asr_arg = False
    max_files = None
    for a in sys.argv:
        if a.startswith("--max-files="):
            max_files = int(a.split("=")[1])
    run(asr=asr_arg, max_files=max_files)

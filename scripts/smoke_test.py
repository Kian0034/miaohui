"""引擎冒烟测试（不含模型）：OCR / 帧采样 / FTS / 加密 / HNSW。
python3 scripts/smoke_test.py
"""
import io
import sys
import tempfile
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))

from core import config  # noqa: E402
config.ensure_dirs()

ok = fail = 0


def check(name, fn):
    global ok, fail
    t0 = time.time()
    try:
        detail = fn()
        ok += 1
        print(f"PASS {name} ({time.time()-t0:.2f}s) {detail or ''}")
    except Exception as e:
        fail += 1
        print(f"FAIL {name}: {type(e).__name__} {e}")


def t_ocr():
    from PIL import Image, ImageDraw
    from core.ocr import ocr_from_pil
    im = Image.new("RGB", (640, 200), "white")
    d = ImageDraw.Draw(im)
    from PIL import ImageFont
    f = None
    for fp in ("/System/Library/Fonts/Hiragino Sans GB.ttc",
               "/System/Library/Fonts/STHeiti Medium.ttc",
               "/System/Library/Fonts/Supplemental/Songti.ttc"):
        try:
            f = ImageFont.truetype(fp, 48)
            break
        except OSError:
            continue
    d.text((40, 60), "秒回本地搜索 0.3秒", fill="black", font=f)
    text = ocr_from_pil(im)
    assert "秒" in text or "0.3" in text, f"OCR 结果: {text!r}"
    return f"-> {text!r}"


def t_frames():
    from core import frames as fm
    path = "/tmp/test_rec.mov"
    assert Path(path).exists(), "缺少测试录像"
    dur, has_v, has_a = fm.probe(path)
    fs = fm.sample_frames(path)
    assert has_v and dur and dur > 1, f"probe 异常 {dur}"
    assert len(fs) >= 1, f"只采到 {len(fs)} 帧"
    thumb = fm.thumb_jpeg(fs[0][1])
    assert len(thumb) > 1000
    return f"dur={dur:.1f}s frames={len(fs)} thumb={len(thumb)}B"


def t_db_fts():
    from core.db import DB, tokenize_query
    with tempfile.TemporaryDirectory() as td:
        db = DB(Path(td) / "t.db")
        fid = db.upsert_file("/tmp/x.jpg", "image", 1.0, 100)
        iid = db.add_item(fid, "image", None, None,
                          "奶油风客厅装修效果图", "", b"\x11")
        hits = db.fts_search(tokenize_query("客厅 装修"), k=5)
        assert iid in [h[0] for h in hits], f"FTS miss: {hits}"
        return f"items={db.stats()['items']}"


def t_crypto():
    from core import security
    payload = "hello 秒回".encode("utf-8") * 100
    blob = security.enc(payload)
    assert security.dec(blob) == payload
    assert blob != payload
    return f"key_in_keychain, blob={len(blob)}B"


def t_hnsw():
    import numpy as np
    from core.db import HNSW
    with tempfile.TemporaryDirectory() as td:
        h = HNSW(Path(td) / "v.bin", 8)
        vecs = np.random.rand(100, 8).astype(np.float32)
        h.add(vecs, list(range(100)))
        h.save()
        h2 = HNSW(Path(td) / "v.bin", 8)
        hits = h2.knn(vecs[7], k=3)
        assert 7 in hits, f"knn miss {hits}"
        return f"n={h2.count}"


def t_clip_introspect():
    """模型存在时才测：ONNX 图输入输出"""
    d = config.MODEL_DIR / "chinese-clip-vit-base-patch16" / "onnx"
    files = [str(p.name) for p in d.glob("*.onnx")] if d.exists() else []
    assert files, f"模型未下载: {d}"
    import onnxruntime as ort
    s = ort.InferenceSession(str(d / files[0]), providers=["CPUExecutionProvider"])
    ins = [(i.name, i.shape) for i in s.get_inputs()]
    outs = [(o.name, o.shape) for o in s.get_outputs()]
    return f"{files[0]} in={ins} out={outs}"


if __name__ == "__main__":
    check("OCR(AppleVision)", t_ocr)
    check("Frames(PyAV)", t_frames)
    check("DB+FTS(jieba)", t_db_fts)
    check("AES-GCM+Keychain", t_crypto)
    check("HNSW", t_hnsw)
    check("CLIP-ONNX", t_clip_introspect)
    print(f"\n== {ok} passed, {fail} failed ==")
    sys.exit(1 if fail else 0)

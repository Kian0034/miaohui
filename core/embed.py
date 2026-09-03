"""嵌入模型层：Chinese-CLIP（图文同空间）+ bge-small-zh（文本语义）。

模型来自 HF 镜像（Xenova 导出的 ONNX），初始化时对 ONNX 图做自动探测：
- 分离式 vision/text 模型（优先）
- 输出为 [N,512] 直接用；为 [N,L,768] 时取 CLS 后需要投影（仅当图内含投影时才可能出现 rank2）
"""
import json
from pathlib import Path

import numpy as np
from PIL import Image

from .config import MODEL_DIR

CLIP_DIR = MODEL_DIR / "chinese-clip-vit-base-patch16"
BGE_DIR = MODEL_DIR / "bge-small-zh-v1.5"

CLIP_MEAN = np.array([0.48145466, 0.4578275, 0.40821073], dtype=np.float32)
CLIP_STD = np.array([0.26862954, 0.26130258, 0.27577711], dtype=np.float32)

BGE_QUERY_PREFIX = "为这个句子生成表示以用于检索相关文章："


def _pick_model_file(d: Path) -> Path:
    for name in ("model_quantized.onnx", "model.onnx",
                 "model_vision_quantized.onnx", "model_vision.onnx",
                 "model_text.onnx"):
        p = d / "onnx" / name
        if p.exists():
            return p
    # 任意 onnx 兜底
    cands = sorted(d.rglob("*.onnx"))
    if cands:
        return cands[0]
    raise FileNotFoundError(f"no onnx model under {d}")


def _io_names(sess):
    ins = [i.name for i in sess.get_inputs()]
    outs = [o.name for o in sess.get_outputs()]
    shapes = [(list(o.shape or [])) for o in sess.get_outputs()]
    return ins, outs, shapes


class _Session:
    def __init__(self, path: Path):
        import onnxruntime as ort
        so = ort.SessionOptions()
        so.log_severity_level = 3
        self.sess = ort.InferenceSession(str(path), so,
                                         providers=["CPUExecutionProvider"])

    def run(self, feeds: dict) -> list:
        return self.sess.run(None, feeds)


class ClipEncoder:
    """Chinese-CLIP：encode_image(PIL)->512d / encode_text(str)->512d"""

    def __init__(self):
        self.tok = None
        self.text_sess = None
        self.vis_sess = None
        self._load()

    def _load(self):
        from tokenizers import Tokenizer
        tok_path = CLIP_DIR / "tokenizer.json"
        self.tok = Tokenizer.from_file(str(tok_path))
        self.tok.enable_truncation(max_length=52)
        self.tok.enable_padding(length=52)

        # Xenova 合并图：单 session，text/vision 输入都必填，
        # 未用的模态喂零/最小张量，取对应 embeds 输出
        s = _Session(_pick_model_file(CLIP_DIR))
        ins, outs, shapes = _io_names(s.sess)
        self.sess = s
        self.in_ids = next((n for n in ins
                            if "ids" in n.lower() or "input" in n.lower()),
                           ins[0])
        self.in_mask = next((n for n in ins if "mask" in n.lower()), None)
        self.in_pix = next((n for n in ins if "pixel" in n.lower()), None)
        self.out_text = next((i for i, o in enumerate(outs)
                              if "text_embeds" in o.lower()), None)
        self.out_image = next((i for i, o in enumerate(outs)
                               if "image_embeds" in o.lower()), None)
        if self.out_text is None or self.out_image is None:
            raise RuntimeError(f"CLIP combined model outputs unexpected: {outs}")
        # 视觉侧的 dummy 文本输入（[CLS][SEP]，最短序列）
        self.dummy_ids = np.array([[101, 102]], dtype=np.int64)
        self.dummy_pix = np.zeros((1, 3, 224, 224), dtype=np.float32)

    # ---------- image ----------
    def _preprocess(self, im: Image.Image) -> np.ndarray:
        im = im.convert("RGB")
        w, h = im.size
        scale = 224 / min(w, h)
        im = im.resize((max(224, int(w * scale + 0.5)),
                        max(224, int(h * scale + 0.5))), Image.BICUBIC)
        w, h = im.size
        l = (w - 224) // 2
        t = (h - 224) // 2
        im = im.crop((l, t, l + 224, t + 224))
        x = np.asarray(im, dtype=np.float32) / 255.0
        x = (x - CLIP_MEAN) / CLIP_STD
        x = x.transpose(2, 0, 1)[None]  # 1,3,224,224
        return np.ascontiguousarray(x)

    def encode_image(self, im: Image.Image) -> np.ndarray:
        feeds = {self.in_pix: self._preprocess(im),
                 self.in_ids: self.dummy_ids}
        if self.in_mask:
            feeds[self.in_mask] = np.ones_like(self.dummy_ids)
        out = self.sess.run(feeds)[self.out_image]
        v = out / (np.linalg.norm(out, axis=-1, keepdims=True) + 1e-9)
        return v[0].astype(np.float32)

    # ---------- text ----------
    def encode_text(self, s: str) -> np.ndarray:
        enc = self.tok.encode(s)
        ids = np.array([enc.ids], dtype=np.int64)
        att = np.array([enc.attention_mask], dtype=np.int64)
        feeds = {self.in_ids: ids, self.in_pix: self.dummy_pix}
        if self.in_mask:
            feeds[self.in_mask] = att
        out = self.sess.run(feeds)[self.out_text]
        v = out / (np.linalg.norm(out, axis=-1, keepdims=True) + 1e-9)
        return v[0].astype(np.float32)


class BgeEncoder:
    """bge-small-zh-v1.5：文本→512d，掩码均值池化 + L2。"""

    def __init__(self):
        from tokenizers import Tokenizer
        tok_path = BGE_DIR / "tokenizer.json"
        self.tok = Tokenizer.from_file(str(tok_path))
        self.tok.enable_truncation(max_length=256)
        path = _pick_model_file(BGE_DIR)
        s = _Session(path)
        ins, outs, shapes = _io_names(s.sess)
        # 优先取 sentence_embedding / rank2 384；否则 last_hidden_state 自池化
        self.pooled_idx = next((i for i, o in enumerate(outs)
                                if "sentence" in o.lower()), None)
        if self.pooled_idx is not None:
            self.out_idx = self.pooled_idx
            self.self_pool = False
        else:
            self.out_idx = 0
            self.self_pool = True
        self.sess = s
        self.in_ids = next((n for n in ins if "input" in n.lower()), ins[0])
        self.in_mask = next((n for n in ins if "mask" in n.lower()), None)
        self.in_types = next((n for n in ins if "token_type" in n.lower()),
                             None)

    def encode(self, s: str) -> np.ndarray:
        enc = self.tok.encode(BGE_QUERY_PREFIX + s)
        ids = np.array([enc.ids], dtype=np.int64)
        att = np.array([enc.attention_mask], dtype=np.int64)
        feeds = {self.in_ids: ids}
        if self.in_mask:
            feeds[self.in_mask] = att
        if self.in_types:
            feeds[self.in_types] = np.zeros_like(ids)
        out = self.sess.run(feeds)[self.out_idx]
        if self.self_pool:
            m = att[0][:, None].astype(np.float32)
            v = (out[0] * m).sum(0) / (m.sum() + 1e-9)
        else:
            v = out[0]
        v = v / (np.linalg.norm(v) + 1e-9)
        return v.astype(np.float32)


_clip = None
_bge = None


def clip() -> ClipEncoder:
    global _clip
    if _clip is None:
        _clip = ClipEncoder()
    return _clip


def bge() -> BgeEncoder:
    global _bge
    if _bge is None:
        _bge = BgeEncoder()
    return _bge

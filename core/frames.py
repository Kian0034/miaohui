"""视频帧采样与音频提取（PyAV）。

策略（速度/覆盖平衡）：
- 短视频(≤10min)：线性解码，按 FRAME_INTERVAL_S 采样
- 长视频：包级遍历取关键帧时间轴，均匀选点后仅解码所选关键帧
- 静止画面去重：24x14 灰度均值差 < 阈值跳过
- 音频：重采样 16k 单声道，最长 30 分钟，供 ASR
"""
import io
from typing import List, Optional, Tuple

import av
import numpy as np
from PIL import Image

from . import config
from .ocr import ImageResample


def _gray_sig(im: Image.Image) -> np.ndarray:
    g = im.convert("L").resize((24, 14), Image.BILINEAR)
    return np.asarray(g, dtype=np.float32)


def thumb_jpeg(im: Image.Image) -> bytes:
    rgb = im.convert("RGB")
    w, h = rgb.size
    scale = config.THUMB_SIZE / max(w, h)
    if scale < 1:
        rgb = rgb.resize((int(w * scale + 0.5), int(h * scale + 0.5)),
                         ImageResample())
    buf = io.BytesIO()
    rgb.save(buf, "JPEG", quality=config.THUMB_JPEG_QUALITY)
    return buf.getvalue()


def probe(path: str) -> Tuple[Optional[float], bool, bool]:
    """返回 (时长秒, 有视频流, 有音频流)"""
    try:
        with av.open(path) as c:
            dur = None
            if c.duration is not None:
                dur = float(c.duration) / av.time_base.AV_TIME_BASE \
                    if hasattr(av.time_base, "AV_TIME_BASE") \
                    else float(c.duration) / 1_000_000
            has_v = any(s.type == "video" for s in c.streams)
            has_a = any(s.type == "audio" for s in c.streams)
            return dur, has_v, has_a
    except Exception:
        return None, False, False


def sample_frames(path: str) -> List[Tuple[float, Image.Image]]:
    """返回 [(t秒, PIL RGB)]，调用方负责 thumb/OCR/嵌入。"""
    frames: List[Tuple[float, Image.Image]] = []
    interval = config.FRAME_INTERVAL_S
    max_frames = config.MAX_FRAMES_PER_VIDEO
    prev_sig = None
    try:
        with av.open(path) as c:
            vs = next((s for s in c.streams if s.type == "video"), None)
            if vs is None:
                return frames
            dur = None
            try:
                if c.duration is not None:
                    dur = float(c.duration) / 1_000_000
            except Exception:
                pass

            if dur is not None and dur > 600:
                # ---- 长视频：关键帧选点 ----
                kf_ts = []
                c.seek(0, stream=vs)
                for pkt in c.demux(vs):
                    if pkt.is_keyframe and pkt.pts is not None:
                        t = float(pkt.pts * pkt.time_base)
                        kf_ts.append(t)
                if not kf_ts:
                    return frames
                targets: List[float] = []
                last = -1e9
                for t in kf_ts:
                    if t - last >= interval:
                        targets.append(t)
                        last = t
                if len(targets) > max_frames:
                    step = len(targets) / max_frames
                    targets = [targets[int(i * step)]
                               for i in range(max_frames)]
                for t in targets:
                    try:
                        tb = vs.time_base
                        c.seek(int(t / tb), stream=vs, backward=True,
                               any_frame=False)
                        got = None
                        for fr in c.decode(vs):
                            got = fr
                            break
                        if got is None:
                            continue
                        ft = float(got.time if got.time is not None else t)
                        im = got.to_image()
                        sig = _gray_sig(im)
                        if prev_sig is not None and np.abs(
                                sig - prev_sig).mean() < config.FRAME_DIFF_THRESHOLD:
                            continue
                        prev_sig = sig
                        frames.append((ft, im))
                        if len(frames) >= max_frames:
                            break
                    except Exception:
                        continue
            else:
                # ---- 短视频：线性解码 ----
                next_t = 0.0
                for fr in c.decode(video=0):
                    t = float(fr.time) if fr.time is not None else 0.0
                    if t + 1e-6 < next_t:
                        continue
                    im = fr.to_image()
                    sig = _gray_sig(im)
                    if prev_sig is not None and np.abs(
                            sig - prev_sig).mean() < config.FRAME_DIFF_THRESHOLD:
                        next_t = t + interval
                        continue
                    prev_sig = sig
                    frames.append((t, im))
                    next_t = t + interval
                    if len(frames) >= max_frames:
                        break
    except Exception:
        pass
    return frames


def extract_audio(path: str, max_seconds: float = 1800.0) -> Optional[np.ndarray]:
    """提取音频为 float32 16k 单声道。无声/失败返回 None。"""
    chunks: list = []
    try:
        with av.open(path) as c:
            asr = None
            ast = next((s for s in c.streams if s.type == "audio"), None)
            if ast is None:
                return None
            res = av.AudioResampler(format="s16", layout="mono", rate=16000)
            total = 0.0
            for fr in c.decode(ast):
                if fr is None:
                    continue
                for out in res.resample(fr):
                    arr = out.to_ndarray()
                    chunks.append(arr)
                    total += arr.shape[1] if arr.ndim > 1 else arr.shape[0]
                    if total >= max_seconds * 16000:
                        break
                if total >= max_seconds * 16000:
                    break
        if not chunks:
            return None
        cat = np.concatenate([c.reshape(-1) for c in chunks])
        if cat.size < 8000:  # <0.5s，无价值
            return None
        return cat.astype(np.float32) / 32768.0
    except Exception:
        return None

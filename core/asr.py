"""ASR：faster-whisper（CTranslate2 int8），带时间戳的中文语音段落。"""
from typing import List, Tuple

from . import config

_model = None

# 音量门限：整段 RMS 低于此值视为静音跳过
_RMS_GATE = 1e-4


def load(model_size: str = "small"):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        local = config.MODEL_DIR / "faster-whisper-small"
        src = str(local) if local.exists() else model_size
        _model = WhisperModel(src, device="cpu", compute_type="int8",
                              cpu_threads=4, num_workers=1)
    return _model


def transcribe(pcm16k, language: str = None) -> List[Tuple[float, float, str]]:
    """输入 16k float32 单声道，返回 [(start, end, text)]。"""
    import numpy as np
    if pcm16k is None or pcm16k.size < 8000:
        return []
    rms = float(np.sqrt(np.mean(np.square(pcm16k))))
    if rms < _RMS_GATE:
        return []
    try:
        model = load()
        segments, _info = model.transcribe(
            pcm16k,
            language=language,
            beam_size=2,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500},
            condition_on_previous_text=False,
        )
        out = []
        for seg in segments:
            t = (seg.text or "").strip()
            if t and seg.end - seg.start > 0.2:
                out.append((float(seg.start), float(seg.end), t))
        return out
    except Exception:
        return []

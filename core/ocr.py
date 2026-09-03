"""OCR：跨平台。macOS 用 Apple Vision，Windows 用 RapidOCR（纯离线 ONNX）。"""
import io
import sys


def ocr_from_jpeg(jpeg_bytes: bytes) -> str:
    """输入 JPEG 字节，返回识别文本（换行连接）。失败返回空串。"""
    try:
        if sys.platform == "win32":
            return _ocr_win(jpeg_bytes)
        return _ocr_mac(jpeg_bytes)
    except Exception:
        return ""


def _ocr_mac(jpeg_bytes: bytes) -> str:
    import Vision
    from Foundation import NSData

    data = NSData.dataWithBytes_length_(jpeg_bytes, len(jpeg_bytes))
    handler = Vision.VNImageRequestHandler.alloc().initWithData_options_(
        data, None)
    req = Vision.VNRecognizeTextRequest.alloc().init()
    req.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    req.setRecognitionLanguages_(["zh-Hans", "zh-Hant", "en-US"])
    req.setUsesLanguageCorrection_(True)
    ok, err = handler.performRequests_error_([req], None)
    if not ok:
        return ""
    lines = []
    for obs in req.results():
        cand = obs.topCandidates_(1)
        if cand:
            s = cand[0].string()
            if s and s.strip():
                lines.append(s.strip())
    return "\n".join(lines)


_ocr_engine = None


def _ocr_win(jpeg_bytes: bytes) -> str:
    global _ocr_engine
    import numpy as np

    if _ocr_engine is None:
        from rapidocr_onnxruntime import RapidOCR
        _ocr_engine = RapidOCR()
    import cv2
    arr = np.frombuffer(jpeg_bytes, np.uint8)
    img = cv2.imdecode(arr, cv2.IMREAD_COLOR)
    if img is None:
        return ""
    result, _ = _ocr_engine(img)
    if not result:
        return ""
    lines = [r[1] for r in result if r and len(r) > 1 and r[1].strip()]
    return "\n".join(lines)


def ocr_from_pil(im) -> str:
    """PIL 图像 → 渲染成高质量 JPEG 再 OCR。"""
    from .config import OCR_SIZE
    from PIL import Image
    buf = io.BytesIO()
    rgb = im.convert("RGB")
    w, h = rgb.size
    scale = OCR_SIZE / max(w, h)
    if scale < 1:
        try:
            rs = Image.Resampling.LANCZOS
        except AttributeError:
            rs = Image.LANCZOS
        rgb = rgb.resize((int(w * scale + 0.5), int(h * scale + 0.5)), rs)
    rgb.save(buf, "JPEG", quality=88)
    return ocr_from_jpeg(buf.getvalue())


def ImageResample():
    try:
        from PIL import Image
        return Image.Resampling.LANCZOS
    except AttributeError:
        from PIL import Image
        return Image.LANCZOS

"""OCR：Apple Vision 框架（准确率高、原生支持简繁中文，M1 上极快）。"""
import io


def ocr_from_jpeg(jpeg_bytes: bytes) -> str:
    """输入 JPEG 字节，返回识别文本（换行连接）。失败返回空串。"""
    try:
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
    except Exception:
        return ""


def ocr_from_pil(im) -> str:
    """PIL 图像 → 渲染成高质量 JPEG 再 OCR。"""
    from .config import OCR_SIZE
    buf = io.BytesIO()
    rgb = im.convert("RGB")
    w, h = rgb.size
    scale = OCR_SIZE / max(w, h)
    if scale < 1:
        rgb = rgb.resize((int(w * scale + 0.5), int(h * scale + 0.5)),
                         ImageResample())
    rgb.save(buf, "JPEG", quality=88)
    return ocr_from_jpeg(buf.getvalue())


def ImageResample():
    try:
        from PIL import Image
        return Image.Resampling.LANCZOS
    except AttributeError:
        from PIL import Image
        return Image.LANCZOS

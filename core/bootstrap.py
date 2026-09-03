"""模型自举：首次运行自动从 HF 镜像下载三个模型（无需外网）。

模型目录：config.MODEL_DIR（~/Library/Application Support/MiaoHui/models）
"""
import threading

from . import config

os_environ_setup = False


def _setup_env():
    global os_environ_setup
    if os_environ_setup:
        return
    import os
    os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
    os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
    os_environ_setup = True


def _want() -> list:
    """→ [(repo, patterns, target_dir)]"""
    return [
        ("Xenova/chinese-clip-vit-base-patch16",
         ["onnx/model_quantized.onnx", "onnx/model.onnx",
          "tokenizer.json", "config.json", "preprocessor_config.json"],
         config.MODEL_DIR / "chinese-clip-vit-base-patch16"),
        ("Xenova/bge-small-zh-v1.5",
         ["onnx/model_quantized.onnx", "tokenizer.json", "config.json"],
         config.MODEL_DIR / "bge-small-zh-v1.5"),
        ("Systran/faster-whisper-small",
         ["model.bin", "config.json", "tokenizer.json",
          "preprocessor_config.json", "vocabulary.json", "vocabulary.txt"],
         config.MODEL_DIR / "faster-whisper-small"),
    ]


def models_ready() -> bool:
    for _repo, _pats, d in _want():
        if not d.exists() or not any(d.rglob("*.onnx")) and not (
                d / "model.bin").exists():
            return False
    return True


def download(progress=None):
    """progress: fn(str) 状态回调（阻塞，直到全部完成或抛异常）。"""
    _setup_env()
    from huggingface_hub import snapshot_download
    for repo, patterns, d in _want():
        if progress:
            progress(f"下载模型 {repo.split('/')[-1]} …")
        snapshot_download(
            repo_id=repo, repo_type="model", allow_patterns=patterns,
            local_dir=str(d), max_workers=4)
    if progress:
        progress("模型就绪")


def ensure_async(on_done=None, progress=None):
    """后台线程确保模型就绪；on_done(ok: bool) 在完成时回调。"""
    def _work():
        ok = True
        try:
            if not models_ready():
                download(progress)
        except Exception as e:
            ok = False
            if progress:
                progress(f"模型下载失败：{e}")
        if on_done:
            try:
                on_done(ok)
            except Exception:
                pass
    t = threading.Thread(target=_work, daemon=True, name="model-bootstrap")
    t.start()
    return t

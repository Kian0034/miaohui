"""下载模型（HF 镜像 hf-mirror.com，无需外网）。

- Chinese-CLIP ViT-B/16 ONNX（Xenova 导出）：视觉+文本分离模型
- bge-small-zh-v1.5 ONNX：中文文本语义
- faster-whisper small（int8 运行时下载到模型目录）
用法：python3 scripts/download_models.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
os.environ.setdefault("HF_HUB_DISABLE_XET", "1")  # xet 直连 hf.co，镜像下不稳

MODEL_DIR = Path.home() / "Library" / "Application Support" / "MiaoHui" / "models"


def dl(repo: str, patterns: list, target: str):
    from huggingface_hub import snapshot_download
    print(f"[dl] {repo} -> {target} ...", flush=True)
    p = snapshot_download(
        repo_id=repo,
        repo_type="model",
        allow_patterns=patterns,
        local_dir=str(MODEL_DIR / target),
        max_workers=4,
    )
    print(f"[dl] done: {p}", flush=True)


def main():
    dl("Xenova/chinese-clip-vit-base-patch16",
       ["onnx/*", "tokenizer.json", "config.json", "preprocessor_config.json"],
       "chinese-clip-vit-base-patch16")
    dl("Xenova/bge-small-zh-v1.5",
       ["onnx/*", "tokenizer.json", "config.json"],
       "bge-small-zh-v1.5")
    dl("Systran/faster-whisper-small",
       ["model.bin", "config.json", "tokenizer.json", "preprocessor_config.json",
        "vocabulary.json", "vocabulary.txt"],
       "faster-whisper-small")
    print("[dl] ALL MODELS READY", flush=True)


if __name__ == "__main__":
    sys.exit(main())

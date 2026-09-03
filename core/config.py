"""秒回 MiaoHui - 全局配置与路径管理（跨平台）。

macOS: ~/Library/Application Support/MiaoHui
Windows: %APPDATA%/MiaoHui
  index.db      SQLite 元数据 + FTS 全文索引 + 加密缩略图
  hnsw_vis.bin  视觉向量 HNSW（Chinese-CLIP 512维）
  hnsw_txt.bin  文本向量 HNSW（bge-small-zh 512维）
  audit.jsonl   审计日志：记录每一个被索引的文件
  settings.json 用户设置
隐私承诺：全程离线，无任何网络请求；缩略图 AES-GCM 加密，
密钥存 macOS 钥匙串 / Windows DPAPI。
"""
import json
import os
import sys
from pathlib import Path

APP_NAME = "MiaoHui"
APP_NAME_CN = "秒回"

if sys.platform == "win32":
    SUPPORT_DIR = (Path(os.environ.get("APPDATA", Path.home() / "AppData"
                                      / "Roaming")) / APP_NAME)
else:
    SUPPORT_DIR = Path.home() / "Library" / "Application Support" / APP_NAME
CACHE_DIR = SUPPORT_DIR / "cache"
DB_PATH = SUPPORT_DIR / "index.db"
HNSW_VIS_PATH = SUPPORT_DIR / "hnsw_vis.bin"
HNSW_TXT_PATH = SUPPORT_DIR / "hnsw_txt.bin"
AUDIT_PATH = SUPPORT_DIR / "audit.jsonl"
SETTINGS_PATH = SUPPORT_DIR / "settings.json"
MODEL_DIR = SUPPORT_DIR / "models"
KEYCHAIN_SERVICE = "MiaoHui-index-key"
KEYCHAIN_ACCOUNT = "thumbs"

# 视觉向量维度（Chinese-CLIP ViT-B/16）
DIM_VIS = 512
# 文本向量维度（bge-small-zh-v1.5，注意中文版是 512 维而非 384）
DIM_TXT = 512

# 默认扫描根目录（顺序即优先级）
if sys.platform == "win32":
    DEFAULT_ROOTS = [
        "~/Downloads",
        "~/Desktop",
        "~/Videos",
        "~/Documents",
        "~/Pictures",
    ]
else:
    DEFAULT_ROOTS = [
        "~/Downloads",
        "~/Desktop",
        "~/Movies",
        "~/vdown_promo",
        "~/xsy_mod",
        "~/Documents",
        "~/Pictures",
        "~/Music",
        "~/vdown",
        "~/cubeforge",
        "~/mcbedrock_finder",
        "~/miyu",
        "~/LiveWall",
    ]

# 媒体扩展名（.ts 与 TypeScript 冲突，不作为视频扩展）
IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif", ".webp", ".gif", ".bmp", ".tiff", ".tif", ".jfif"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".mkv", ".avi", ".webm", ".flv", ".wmv", ".3gp", ".mpg", ".mpeg"}

# 单文件大小上限（不索引超大文件，避免磁盘压力）
MAX_IMAGE_BYTES = 80 * 1024 * 1024
MAX_VIDEO_BYTES = 3 * 1024 * 1024 * 1024

# 视频采样策略：每 FRAME_INTERVAL_S 秒一帧，单视频最多 MAX_FRAMES_PER_VIDEO 帧
FRAME_INTERVAL_S = 3.0
MAX_FRAMES_PER_VIDEO = 180
# 相邻帧灰度差阈值（0-255），低于此值视为静止画面跳过
FRAME_DIFF_THRESHOLD = 6.0

# 缩略图参数
THUMB_SIZE = 192          # 存储/展示缩略图边长
OCR_SIZE = 640            # OCR 使用的渲染边长
THUMB_JPEG_QUALITY = 68

# 排除目录名（任何层级命中即整棵跳过）
EXCLUDED_DIR_NAMES = {
    "node_modules", ".git", "__pycache__", ".venv", "venv", "site-packages",
    "Library", ".Trash", ".gradle", ".android", ".cache", ".npm",
    "DerivedData", "build", "target", "dist", ".next",
    "wechatvideo", "Steam", "steamapps",
}

# 敏感内容保护（信任包核心，默认开启）：
# 命中这些规则的文件一律不索引、不生成缩略图，动作写入审计日志
SENSITIVE_DIR_KEYWORDS = [
    "银行", "bank", "banking", "password", "密码", "credential",
    "1password", "keychain", "钥匙串", "wallet", "钱包", "id-card", "身份证",
    "tax", "报税", "发票", "invoice",
]
SENSITIVE_FILE_KEYWORDS = [
    "password", "密码", "账密", "secret", "token", "credential", "wallet",
    "keystore", "private_key", "id_card", "身份证", "bank_card", "银行卡",
]
# 敏感文件扩展名（密钥/证书类一律不索引）
SENSITIVE_EXTS = {".pem", ".key", ".p12", ".pfx", ".kdbx", ".keystore", ".jks"}


def ensure_dirs():
    SUPPORT_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    MODEL_DIR.mkdir(parents=True, exist_ok=True)


def load_settings() -> dict:
    default = {
        "roots": DEFAULT_ROOTS,
        "sensitive_protection": True,
        "asr_enabled": True,
        "ocr_enabled": True,
        "indexing_paused": False,
    }
    try:
        with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
            saved = json.load(f)
        default.update(saved)
    except Exception:
        pass
    return default


def save_settings(s: dict):
    ensure_dirs()
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        json.dump(s, f, ensure_ascii=False, indent=2)


def expand_roots(settings: dict) -> list:
    out = []
    for r in settings.get("roots", DEFAULT_ROOTS):
        p = Path(os.path.expanduser(r))
        if p.exists() and p.is_dir():
            out.append(p)
    return out

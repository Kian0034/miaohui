"""文件扫描器：全量遍历 + 敏感内容排除（信任包第二支柱）。"""
import os
import time
from pathlib import Path
from typing import Iterator

from . import config
from .security import audit


def _is_sensitive(path: Path) -> bool:
    """敏感保护：目录关键词 / 文件关键词 / 密钥类扩展名。"""
    name = path.name.lower()
    if path.suffix.lower() in config.SENSITIVE_EXTS:
        return True
    for kw in config.SENSITIVE_FILE_KEYWORDS:
        if kw in name:
            return True
    for p in path.parents:
        pl = p.name.lower()
        for kw in config.SENSITIVE_DIR_KEYWORDS:
            if kw in pl:
                return True
    return False


def scan(roots, sensitive: bool = True) -> Iterator[Path]:
    """遍历所有根目录，产出待索引媒体文件。"""
    for root in roots:
        root = Path(root)
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
            # 剪枝：排除目录名 + 隐藏目录 + 敏感目录
            pruned = []
            for d in list(dirnames):
                if d.startswith(".") or d in config.EXCLUDED_DIR_NAMES:
                    dirnames.remove(d)
                    continue
                if sensitive:
                    dl = d.lower()
                    if any(kw in dl for kw in config.SENSITIVE_DIR_KEYWORDS):
                        audit("sensitive_dir_excluded",
                              {"path": os.path.join(dirpath, d)})
                        dirnames.remove(d)
                        continue
                pruned.append(d)
            dirnames[:] = pruned
            for fn in filenames:
                if fn.startswith("."):
                    continue
                ext = os.path.splitext(fn)[1].lower()
                if ext not in config.IMAGE_EXTS and ext not in config.VIDEO_EXTS:
                    continue
                p = Path(dirpath) / fn
                try:
                    st = p.stat()
                except OSError:
                    continue
                if st.st_size < 64:  # 空文件/损坏文件
                    continue
                if st.st_size > (config.MAX_VIDEO_BYTES if ext in config.VIDEO_EXTS
                                 else config.MAX_IMAGE_BYTES):
                    continue
                if sensitive and _is_sensitive(p):
                    audit("sensitive_file_excluded", {"path": str(p)})
                    continue
                yield p


def scan_stats(roots, sensitive=True) -> dict:
    n_img = n_vid = 0
    t0 = time.time()
    for p in scan(roots, sensitive):
        if p.suffix.lower() in config.VIDEO_EXTS:
            n_vid += 1
        else:
            n_img += 1
    return {"images": n_img, "videos": n_vid, "secs": round(time.time() - t0, 1)}

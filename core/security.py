"""信任包第一支柱：本地库加密（跨平台）。

- AES-256-GCM 加密所有缩略图（像素是最敏感的数据）
- macOS：密钥存 Keychain；Windows：密钥经 DPAPI 加密落盘（当前 Windows 用户可解）
- 提供统一的 enc/dec 接口，DB 层无感知
"""
import os
import subprocess
import sys

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import KEYCHAIN_ACCOUNT, KEYCHAIN_SERVICE

_key_cache = None


def get_key() -> bytes:
    """读取 256 位密钥；不存在则生成并写入系统凭据存储。"""
    global _key_cache
    if _key_cache is not None:
        return _key_cache
    if sys.platform == "win32":
        _key_cache = _win_get_key()
    else:
        _key_cache = _mac_get_key()
    return _key_cache


def _mac_get_key() -> bytes:
    r = subprocess.run(
        ["security", "find-generic-password", "-s", KEYCHAIN_SERVICE,
         "-a", KEYCHAIN_ACCOUNT, "-w"],
        capture_output=True, text=True, timeout=10)
    if r.returncode == 0 and r.stdout.strip():
        return bytes.fromhex(r.stdout.strip())
    key = os.urandom(32)
    subprocess.run(
        ["security", "add-generic-password", "-s", KEYCHAIN_SERVICE,
         "-a", KEYCHAIN_ACCOUNT, "-w", key.hex(), "-U"],
        capture_output=True, text=True, timeout=10)
    return key


# ---------- Windows DPAPI ----------
_dpapi = None


def _dpapi_blob(data: bytes):
    import ctypes
    from ctypes import wintypes

    class DATA_BLOB(ctypes.Structure):
        _fields_ = [("cbData", wintypes.DWORD),
                    ("pbData", ctypes.POINTER(ctypes.c_char))]

    buf = ctypes.create_string_buffer(data, len(data))
    blob_in = DATA_BLOB(len(data), ctypes.cast(buf,
                                              ctypes.POINTER(ctypes.c_char)))
    blob_out = DATA_BLOB()
    return blob_in, blob_out


def _win_get_key() -> bytes:
    import ctypes
    from pathlib import Path

    from .config import SUPPORT_DIR
    f = Path(SUPPORT_DIR) / "key.dpapi"
    f.parent.mkdir(parents=True, exist_ok=True)
    crypt32 = ctypes.windll.crypt32
    kernel32 = ctypes.windll.kernel32

    def protect(data: bytes) -> bytes:
        blob_in, blob_out = _dpapi_blob(data)
        if not crypt32.CryptProtectData(
                ctypes.byref(blob_in), "MiaoHui", None, None, None, 0,
                ctypes.byref(blob_out)):
            raise OSError("DPAPI protect failed")
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        kernel32.LocalFree(blob_out.pbData)
        return out

    def unprotect(data: bytes) -> bytes:
        blob_in, blob_out = _dpapi_blob(data)
        if not crypt32.CryptUnprotectData(
                ctypes.byref(blob_in), None, None, None, None, 0,
                ctypes.byref(blob_out)):
            raise OSError("DPAPI unprotect failed")
        out = ctypes.string_at(blob_out.pbData, blob_out.cbData)
        kernel32.LocalFree(blob_out.pbData)
        return out

    if f.exists():
        key = unprotect(f.read_bytes())
        if len(key) == 32:
            return key
    key = os.urandom(32)
    f.write_bytes(protect(key))
    return key


def enc(data: bytes) -> bytes:
    """AES-256-GCM 加密，输出 nonce(12B) + ciphertext。"""
    nonce = os.urandom(12)
    ct = AESGCM(get_key()).encrypt(nonce, data, None)
    return nonce + ct


def dec(blob: bytes) -> bytes:
    return AESGCM(get_key()).decrypt(bytes(blob[:12]), bytes(blob[12:]), None)


def audit(event: str, detail: dict):
    """审计日志：每一次敏感排除、索引动作都可追溯。"""
    import json
    import time
    from .config import AUDIT_PATH, ensure_dirs

    try:
        ensure_dirs()
        rec = {"ts": time.time(), "event": event, **detail}
        with open(AUDIT_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec, ensure_ascii=False) + "\n")
    except Exception:
        pass

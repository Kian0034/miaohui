"""信任包第一支柱：本地库加密。

- AES-256-GCM 加密所有缩略图（像素是最敏感的数据）
- 密钥保存在 macOS 钥匙串（Keychain），任何进程读取都需要用户授权
- 提供统一的 enc/dec 接口，DB 层无感知
"""
import os
import subprocess

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from .config import KEYCHAIN_ACCOUNT, KEYCHAIN_SERVICE

_key_cache = None


def _keychain_cmd(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["security"] + list(args), capture_output=True, text=True, timeout=10
    )


def get_key() -> bytes:
    """从钥匙串读取 256 位密钥；不存在则生成并写入。"""
    global _key_cache
    if _key_cache is not None:
        return _key_cache
    r = _keychain_cmd(
        "find-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT, "-w"
    )
    if r.returncode == 0 and r.stdout.strip():
        _key_cache = bytes.fromhex(r.stdout.strip())
        return _key_cache
    key = os.urandom(32)
    _keychain_cmd(
        "add-generic-password", "-s", KEYCHAIN_SERVICE, "-a", KEYCHAIN_ACCOUNT,
        "-w", key.hex(), "-U",
    )
    _key_cache = key
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

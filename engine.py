"""
engine.py
Core file-hashing engine for Neural Defender.
"""

import hashlib
import logging

logger = logging.getLogger("NeuralDefender.Engine")

CHUNK_SIZE = 65536  # 64KB chunks - faster than 4KB for large files


def md5_hash(file_path: str) -> str | None:
    """
    Compute the MD5 hash of a file, reading it in chunks so large
    files don't get loaded fully into memory.

    Returns the hex digest string, or None if the file couldn't be read.
    """
    md5 = hashlib.md5()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                md5.update(chunk)
        return md5.hexdigest()
    except FileNotFoundError:
        logger.error("File not found: %s", file_path)
        return None
    except PermissionError:
        logger.error("Permission denied reading: %s", file_path)
        return None
    except OSError as e:
        logger.error("OS error hashing %s: %s", file_path, e)
        return None


def sha256_hash(file_path: str) -> str | None:
    """Compute the SHA-256 hash of a file (stronger than MD5, optional use)."""
    sha256 = hashlib.sha256()
    try:
        with open(file_path, "rb") as f:
            while chunk := f.read(CHUNK_SIZE):
                sha256.update(chunk)
        return sha256.hexdigest()
    except OSError as e:
        logger.error("OS error hashing %s: %s", file_path, e)
        return None

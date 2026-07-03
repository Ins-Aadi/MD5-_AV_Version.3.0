"""
scanner.py
Signature-based file scanner for Neural Defender.
Supports MD5 hash signatures and raw byte-string signatures.
"""

import os
import shutil
import logging
from dataclasses import dataclass
from enum import Enum

from engine import md5_hash

logger = logging.getLogger("NeuralDefender.Scanner")

QUARANTINE_DIR = os.path.join(os.path.expanduser("~"), ".neural_defender", "quarantine")


class ScanStatus(Enum):
    SAFE = "SAFE"
    INFECTED = "INFECTED"
    ERROR = "ERROR"
    NOT_FOUND = "NOT_FOUND"


@dataclass
class ScanResult:
    status: ScanStatus
    file_name: str
    file_path: str
    message: str
    matched_signature: str | None = None
    quarantined_path: str | None = None


def _ensure_quarantine_dir():
    os.makedirs(QUARANTINE_DIR, exist_ok=True)


def quarantine_file(file_path: str) -> str | None:
    """
    Move an infected file to a quarantine folder instead of deleting it,
    so nothing is lost permanently and the action is reversible.
    """
    try:
        _ensure_quarantine_dir()
        file_name = os.path.basename(file_path)
        dest = os.path.join(QUARANTINE_DIR, file_name)

        # Avoid overwriting existing quarantined files with the same name
        counter = 1
        base, ext = os.path.splitext(dest)
        while os.path.exists(dest):
            dest = f"{base}_{counter}{ext}"
            counter += 1

        shutil.move(file_path, dest)
        logger.info("Quarantined %s -> %s", file_path, dest)
        return dest
    except OSError as e:
        logger.error("Failed to quarantine %s: %s", file_path, e)
        return None


def scan_file(file_path: str, signatures) -> ScanResult:
    """
    Scan a single file against a list of (sign_type, sign_value) signatures.
    Does NOT delete or move the file - callers decide what to do with the
    result (e.g. the GUI can ask before quarantining).
    """
    file_name = os.path.basename(file_path)

    if not os.path.isfile(file_path):
        return ScanResult(
            status=ScanStatus.NOT_FOUND,
            file_name=file_name,
            file_path=file_path,
            message=f"File not found: {file_name}",
        )

    if not signatures:
        return ScanResult(
            status=ScanStatus.ERROR,
            file_name=file_name,
            file_path=file_path,
            message="No signatures available (database unreachable or empty).",
        )

    try:
        hash_value = md5_hash(file_path)
        if not hash_value:
            return ScanResult(
                status=ScanStatus.ERROR,
                file_name=file_name,
                file_path=file_path,
                message=f"Could not read/hash file: {file_name}",
            )

        # --- HASH SIGNATURE CHECK ---
        for sign_type, sign_value in signatures:
            if sign_type == "hash" and hash_value == sign_value:
                return ScanResult(
                    status=ScanStatus.INFECTED,
                    file_name=file_name,
                    file_path=file_path,
                    message=f"Infected file detected (hash match): {file_name}",
                    matched_signature=hash_value,
                )

        # --- STRING SIGNATURE CHECK ---
        with open(file_path, "rb") as f:
            content = f.read()

        for sign_type, sign_value in signatures:
            if sign_type == "string":
                needle = sign_value.encode() if isinstance(sign_value, str) else sign_value
                if needle in content:
                    return ScanResult(
                        status=ScanStatus.INFECTED,
                        file_name=file_name,
                        file_path=file_path,
                        message=f"Infected file detected (string match): {file_name}",
                        matched_signature=str(sign_value),
                    )

        return ScanResult(
            status=ScanStatus.SAFE,
            file_name=file_name,
            file_path=file_path,
            message=f"{file_name} is safe.",
        )

    except Exception as e:
        logger.exception("Error scanning %s", file_path)
        return ScanResult(
            status=ScanStatus.ERROR,
            file_name=file_name,
            file_path=file_path,
            message=f"Error scanning {file_name}: {e}",
        )


def scan_directory(dir_path: str, signatures, progress_callback=None) -> list[ScanResult]:
    """
    Recursively scan every file in a directory.
    progress_callback(current_index, total, current_file_name) is called
    after each file if provided, so a GUI can update a progress bar.
    """
    results = []
    all_files = []
    for root, _dirs, files in os.walk(dir_path):
        for fname in files:
            all_files.append(os.path.join(root, fname))

    total = len(all_files)
    for i, fpath in enumerate(all_files, start=1):
        results.append(scan_file(fpath, signatures))
        if progress_callback:
            progress_callback(i, total, os.path.basename(fpath))

    return results

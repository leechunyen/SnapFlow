"""File management utilities for SnapFlow.

Handles temp directory creation, saving temporary screenshot files,
and cleaning up temporary files upon exit.
"""

from __future__ import annotations

import os
import shutil
import tempfile
from pathlib import Path

# Use a process-specific temporary directory to prevent conflicts across multiple SnapFlow instances
TEMP_DIR: Path = Path(tempfile.gettempdir()) / f"SnapFlow_temp_{os.getpid()}"


def ensure_temp_dir() -> Path:
    """Ensures that the instance-specific temporary screenshot directory exists."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return TEMP_DIR


def save_screenshot_bytes(img_bytes: bytes, filename: str) -> Path:
    """Saves raw screenshot bytes to the temp directory and returns its Path."""
    target_path = ensure_temp_dir() / filename
    target_path.write_bytes(img_bytes)
    return target_path


def cleanup_temp_dir() -> None:
    """Removes the entire temporary screenshot directory and its contents."""
    if TEMP_DIR.exists():
        try:
            shutil.rmtree(TEMP_DIR, ignore_errors=True)
        except Exception as e:
            print(f"[file_utils] Error cleaning temp directory: {e}")

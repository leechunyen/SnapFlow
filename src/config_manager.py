"""SnapFlow configuration manager.

Persists settings such as theme and language preferences to ~/.snapflow/config.json.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR: Path = Path.home() / ".snapflow"
CONFIG_FILE: Path = CONFIG_DIR / "config.json"

DEFAULT_CONFIG: dict[str, Any] = {
    "theme": "light",  # Options: "light", "dark", "system"
    "language": None,  # None means auto-detect; otherwise e.g. "en_us", "zh_tw", "ms_my"
    "capture_delay": 1,  # Screenshot settle delay in seconds (1 to 5)
    "last_png_dir": "",
    "last_pdf_dir": "",
}


class ConfigManager:
    """Manages reading and writing application configurations."""

    def __init__(self) -> None:
        self._data: dict[str, Any] = {}
        self._load()

    def _load(self) -> None:
        """Loads configuration from JSON file or initializes defaults."""
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        self._data = loaded
            except (json.JSONDecodeError, OSError):
                self._data = {}

        # Fill in missing keys with default values
        for key, val in DEFAULT_CONFIG.items():
            self._data.setdefault(key, val)

    def save(self) -> None:
        """Persists current configuration to disk."""
        try:
            CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(self._data, f, ensure_ascii=False, indent=2)
        except OSError as e:
            print(f"[ConfigManager] Warning: failed to save config: {e}")

    def get(self, key: str, fallback: Any = None) -> Any:
        """Retrieves a configuration value."""
        return self._data.get(key, fallback if fallback is not None else DEFAULT_CONFIG.get(key))

    def set(self, key: str, value: Any) -> None:
        """Sets a configuration value and saves to disk immediately."""
        self._data[key] = value
        self.save()

    @property
    def theme(self) -> str:
        """Current theme mode ('light', 'dark', or 'system')."""
        t = self.get("theme", "light")
        return t if t in ("light", "dark", "system") else "light"

    @theme.setter
    def theme(self, value: str) -> None:
        if value in ("light", "dark", "system"):
            self.set("theme", value)

    @property
    def language(self) -> str | None:
        """Configured language code or None if auto-detect."""
        lang = self.get("language")
        return lang if isinstance(lang, str) else None

    @language.setter
    def language(self, value: str | None) -> None:
        self.set("language", value)

    @property
    def capture_delay(self) -> int:
        """Configured capture delay in seconds (1 to 5)."""
        val = self.get("capture_delay", 1)
        try:
            val_int = int(val)
            return max(1, min(5, val_int))
        except (ValueError, TypeError):
            return 1

    @capture_delay.setter
    def capture_delay(self, value: int) -> None:
        clamped = max(1, min(5, int(value)))
        self.set("capture_delay", clamped)

    @property
    def last_png_dir(self) -> str:
        """Last directory used for exporting PNGs."""
        return str(self.get("last_png_dir", ""))

    @last_png_dir.setter
    def last_png_dir(self, value: str) -> None:
        self.set("last_png_dir", value)

    @property
    def last_pdf_dir(self) -> str:
        """Last directory used for exporting PDF."""
        return str(self.get("last_pdf_dir", ""))

    @last_pdf_dir.setter
    def last_pdf_dir(self, value: str) -> None:
        self.set("last_pdf_dir", value)

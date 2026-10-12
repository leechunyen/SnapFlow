"""SnapFlow internationalization (i18n) module.

Supports en_us, zh_tw, and ms_my.
Auto-detects system language and falls back to en_us.
"""

from __future__ import annotations

import json
import locale
import os
import sys
from pathlib import Path
from typing import Any

def _resolve_i18n_dir() -> Path:
    """Dynamically resolves the directory containing i18n JSON files across dev and PyInstaller."""
    # 1. PyInstaller bundled environment (_MEIPASS)
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        p_base = Path(meipass)
        # Check both --add-data "src/i18n:i18n" and "src/i18n:src/i18n"
        for candidate in (p_base / "i18n", p_base / "src" / "i18n"):
            if candidate.exists() and (candidate / "en_us.json").exists():
                return candidate

    # 2. Local development environment
    local_dir = Path(__file__).resolve().parent
    if (local_dir / "en_us.json").exists():
        return local_dir

    # 3. Project root fallback
    root_src = local_dir.parent / "i18n"
    if root_src.exists() and (root_src / "en_us.json").exists():
        return root_src

    return local_dir


I18N_DIR: Path = _resolve_i18n_dir()

SUPPORTED_LOCALES: dict[str, str] = {
    # Traditional Chinese mappings
    "zh_tw": "zh_tw",
    "zh-tw": "zh_tw",
    "zh_hk": "zh_tw",
    "zh-hk": "zh_tw",
    "zh_hant": "zh_tw",
    "zh-hant": "zh_tw",
    "zh_hant_tw": "zh_tw",
    "zh-hant-tw": "zh_tw",
    # Malay mappings
    "ms_my": "ms_my",
    "ms-my": "ms_my",
    "ms": "ms_my",
    # English mappings
    "en_us": "en_us",
    "en-us": "en_us",
    "en_gb": "en_us",
    "en": "en_us",
}

FALLBACK_LOCALE: str = "en_us"

_current_locale: str = FALLBACK_LOCALE
_strings: dict[str, str] = {}


def _match_locale(tag: str) -> str | None:
    """Matches a language tag string against supported locales."""
    cleaned = tag.strip().lower().replace("-", "_")
    # Exact match
    if cleaned in SUPPORTED_LOCALES:
        return SUPPORTED_LOCALES[cleaned]
    # Prefix match e.g. zh_cn -> None, ms_sg -> ms_my, en_au -> en_us
    base = cleaned.split("_")[0]
    if base in SUPPORTED_LOCALES:
        return SUPPORTED_LOCALES[base]
    return None


def detect_system_locale() -> str:
    """Detects system language preference."""
    # 1. On macOS, query NSLocale if available
    if sys.platform == "darwin":
        try:
            from Foundation import NSLocale  # type: ignore
            langs = NSLocale.preferredLanguages()
            if langs and len(langs) > 0:
                matched = _match_locale(str(langs[0]))
                if matched:
                    return matched
        except Exception:
            pass

    # 2. Check standard environment variables
    for env in ("LC_ALL", "LC_MESSAGES", "LANG", "LANGUAGE"):
        val = os.environ.get(env, "")
        if val:
            # Drop encoding e.g. "zh_TW.UTF-8" -> "zh_TW"
            raw = val.split(".")[0]
            matched = _match_locale(raw)
            if matched:
                return matched

    # 3. Check Python's locale module
    try:
        locale.setlocale(locale.LC_ALL, "")
        loc = locale.getlocale()
        if loc and loc[0]:
            matched = _match_locale(loc[0])
            if matched:
                return matched
    except Exception:
        pass

    return FALLBACK_LOCALE


_cached_locales: dict[str, dict[str, str]] = {}


def load_strings(locale_name: str) -> dict[str, str]:
    """Loads JSON strings for the specified locale, caching in memory and falling back if not found."""
    if locale_name in _cached_locales:
        return _cached_locales[locale_name]

    target_file = I18N_DIR / f"{locale_name}.json"
    if not target_file.exists():
        target_file = I18N_DIR / f"{FALLBACK_LOCALE}.json"

    try:
        with open(target_file, "r", encoding="utf-8") as f:
            data = json.load(f)
            _cached_locales[locale_name] = data
            return data
    except Exception as e:
        print(f"[i18n] Failed to load {target_file}: {e}")
        return {}


def init(locale_override: str | None = None) -> str:
    """Initializes the translation system.

    Returns the active locale name.
    """
    global _current_locale, _strings

    target = _match_locale(locale_override) if locale_override else None
    if not target:
        target = detect_system_locale()

    _current_locale = target
    _strings = load_strings(_current_locale)
    return _current_locale


def get_current_locale() -> str:
    """Returns the currently active locale identifier."""
    return _current_locale


def t(key: str, **kwargs: Any) -> str:
    """Retrieves localized text by key, optionally formatting with kwargs."""
    raw = _strings.get(key, key)
    if kwargs:
        try:
            return raw.format(**kwargs)
        except Exception:
            return raw
    return raw

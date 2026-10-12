"""SnapFlow entry point.

Starts the CustomTkinter desktop application, initializes configuration,
and sets up internationalization.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from PIL import Image

# Ensure src/ is on sys.path so all imports inside src resolve smoothly
SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Globally disable decompression bomb limits for ultra-large captures
Image.MAX_IMAGE_PIXELS = None

from app import SnapFlowApp
from config_manager import ConfigManager
import i18n


def parse_args() -> argparse.Namespace:
    """Parses optional command-line arguments."""
    parser = argparse.ArgumentParser(description="SnapFlow - Playwright Web Screenshot Tool")
    parser.add_argument(
        "--lang",
        choices=["en_us", "zh_tw", "ms_my"],
        help="Override language (en_us, zh_tw, ms_my)",
        default=None,
    )
    parser.add_argument(
        "--theme",
        choices=["light", "dark", "system"],
        help="Override theme (light, dark, system)",
        default=None,
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    # Load persistent settings
    config_mgr = ConfigManager()

    # Override theme if specified via CLI
    if args.theme:
        config_mgr.theme = args.theme

    # Language resolution: CLI arg > saved config > system auto-detect
    lang_pref = args.lang or config_mgr.language
    active_lang = i18n.init(locale_override=lang_pref)
    print(f"[SnapFlow] Initialized with language: {active_lang}, theme: {config_mgr.theme}")

    # Launch GUI application
    app = SnapFlowApp(config_mgr=config_mgr)

    # Allow clean exit on SIGINT / Ctrl+C in terminal
    def _sigint_handler(sig, frame):
        try:
            app.after(0, app._on_window_close)
        except Exception:
            sys.exit(0)

    try:
        import signal
        signal.signal(signal.SIGINT, _sigint_handler)
    except Exception:
        pass

    try:
        app.mainloop()
    except KeyboardInterrupt:
        try:
            app._on_window_close()
        except Exception:
            pass


if __name__ == "__main__":
    main()

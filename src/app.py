"""Main application window for SnapFlow."""

from __future__ import annotations

import time
from tkinter import messagebox
import customtkinter as ctk

from browser_manager import BrowserManager
from config_manager import ConfigManager
import i18n
from screenshot_model import Screenshot, ScreenshotModel
from ui.dialogs import LoadingDialog, UnsavedChangesDialog
from ui.export_panel import ExportPanel
from ui.preview_panel import PreviewPanel
from ui.toolbar import Toolbar
from utils import file_utils, image_utils


class SnapFlowApp(ctk.CTk):
    """SnapFlow desktop application window."""

    def __init__(self, config_mgr: ConfigManager) -> None:
        self.config_mgr = config_mgr

        # Apply persistent theme preference before window initialization
        ctk.set_appearance_mode(self.config_mgr.theme)
        ctk.set_default_color_theme("blue")

        super().__init__()

        self.title(i18n.t("app_title"))
        self.geometry("1100x700")
        self.minsize(960, 600)
        self._setup_window_icon()

        # Initialize models & browser manager
        self.model = ScreenshotModel()
        self.browser_mgr = BrowserManager(
            capture_delay=self.config_mgr.capture_delay,
            on_browser_started=self._handle_browser_started_event,
            on_browser_closed=self._handle_browser_closed_event,
            on_page_title_changed=self._handle_page_title_event,
            on_tabs_updated=self._handle_tabs_updated_event,
            on_screenshot_captured=self._handle_screenshot_event,
            on_range_start_ready=self._handle_range_start_ready_event,
            on_error=self._handle_browser_error_event,
        )

        self._loading_dialog: LoadingDialog | None = None

        self._build_layout()
        # Register preview panel with CustomTkinter's appearance tracker so theme changes auto-sync
        ctk.AppearanceModeTracker.add(self.preview_panel.update_theme_colors, self)

        self.protocol("WM_DELETE_WINDOW", self._on_window_close)

    def _setup_window_icon(self) -> None:
        """Sets the application window and dock icon from the images/ directory."""
        import sys
        from pathlib import Path
        from PIL import Image, ImageTk

        base_dir = Path(__file__).resolve().parent
        # Look for images/ in project root (parent of src) or inside base_dir / sys._MEIPASS
        bundle_dir = Path(getattr(sys, "_MEIPASS", base_dir.parent if base_dir.name == "src" else base_dir))
        ico_path = (bundle_dir / "images" / "icon.ico") if (bundle_dir / "images" / "icon.ico").exists() else (base_dir / "images" / "icon.ico")
        png_path = (bundle_dir / "images" / "icon.png") if (bundle_dir / "images" / "icon.png").exists() else (base_dir / "images" / "icon.png")
        icns_path = (bundle_dir / "images" / "icon.icns") if (bundle_dir / "images" / "icon.icns").exists() else (base_dir / "images" / "icon.icns")

        try:
            # 1. On Windows, use .ico directly
            if sys.platform.startswith("win") and ico_path.exists():
                self.iconbitmap(str(ico_path))
            # 2. Cross-platform / Linux / Windows wm_iconphoto
            elif png_path.exists():
                with Image.open(png_path) as img:
                    # Provide iconphoto for title bar and taskbar
                    self._icon_photo = ImageTk.PhotoImage(img.resize((64, 64), Image.Resampling.LANCZOS))
                    self.wm_iconphoto(True, self._icon_photo)
        except Exception as e:
            print(f"[SnapFlow] Note: Window icon could not be set: {e}")

        # 3. macOS Dock icon support via Cocoa API if available
        if sys.platform == "darwin":
            try:
                from AppKit import NSApplication, NSImage  # type: ignore
                app = NSApplication.sharedApplication()
                target_icon_path = str(icns_path if icns_path.exists() else png_path)
                ns_img = NSImage.alloc().initWithContentsOfFile_(target_icon_path)
                if ns_img:
                    app.setApplicationIconImage_(ns_img)
            except Exception:
                pass

    def _build_layout(self) -> None:
        """Constructs and packs the main application subcomponents."""
        # Top toolbar
        self.toolbar = Toolbar(
            self,
            config_mgr=self.config_mgr,
            on_launch=self._on_launch_browser,
            on_new_tab=self._on_new_tab,
            on_viewport=lambda: self._on_capture_screenshot(full_page=False),
            on_fullpage=lambda: self._on_capture_screenshot(full_page=True),
            on_range_start=self._on_range_start,
            on_range_confirm=self._on_range_confirm,
            on_range_cancel=self._on_range_cancel,
            on_theme_changed=self._on_theme_changed,
            on_language_changed=self._on_language_changed,
            on_delay_changed=self._on_delay_changed,
            on_tab_selected=self._on_tab_selected,
        )
        self.toolbar.pack(fill="x", side="top")

        # Center preview panel
        self.preview_panel = PreviewPanel(
            self,
            model=self.model,
            on_list_changed=self._on_list_updated,
        )
        self.preview_panel.pack(fill="both", expand=True, side="top", padx=14, pady=(6, 4))

        # Bottom export panel
        self.export_panel = ExportPanel(
            self,
            model=self.model,
            config_mgr=self.config_mgr,
            get_selected_indices=self.preview_panel.get_selected_indices,
        )
        self.export_panel.pack(fill="x", side="bottom")

    # ------------------ Action Handlers ------------------

    def _on_launch_browser(self) -> None:
        """Launches the automated Chromium browser."""
        self.toolbar.btn_launch.configure(state="disabled")
        self.browser_mgr.launch()

    def _on_new_tab(self) -> None:
        """Requests browser to open a new tab."""
        if not self.browser_mgr.is_running:
            messagebox.showwarning(i18n.t("app_title"), i18n.t("error_no_browser"))
            return
        self.browser_mgr.request_new_tab()

    def _show_loading(self, message: str) -> None:
        """Displays a modal loading indicator preventing user interaction."""
        if self._loading_dialog is None:
            self._loading_dialog = LoadingDialog(self, message)

    def _hide_loading(self) -> None:
        """Dismisses the modal loading indicator."""
        if self._loading_dialog is not None:
            self._loading_dialog.close()
            self._loading_dialog = None

    def _on_capture_screenshot(self, full_page: bool) -> None:
        """Requests screenshot capture from the active browser tab."""
        if not self.browser_mgr.is_running:
            messagebox.showwarning(i18n.t("app_title"), i18n.t("error_no_browser"))
            return
        self._show_loading(i18n.t("loading_capturing"))
        self.browser_mgr.request_screenshot(full_page=full_page)

    def _on_range_start(self) -> None:
        """Starts scroll range capture mode by recording current scroll position."""
        if not self.browser_mgr.is_running:
            messagebox.showwarning(i18n.t("app_title"), i18n.t("error_no_browser"))
            return
        self.browser_mgr.request_start_range_capture()

    def _on_range_confirm(self) -> None:
        """Confirms capture from start position down to current scrolled position."""
        if not self.browser_mgr.is_running:
            return
        self._show_loading(i18n.t("loading_capturing"))
        self.browser_mgr.request_confirm_range_capture()

    def _on_range_cancel(self) -> None:
        """Cancels range capture mode."""
        self.browser_mgr.cancel_range_capture()

    def _on_theme_changed(self, new_mode: str) -> None:
        """Applies and saves theme change."""
        self.config_mgr.theme = new_mode

        if new_mode == "system":
            import darkdetect
            ctk.set_appearance_mode("system")
            sys_mode = 1 if darkdetect.theme() == "Dark" else 0
            ctk.AppearanceModeTracker.appearance_mode = sys_mode
            ctk.AppearanceModeTracker.update_callbacks()
        else:
            ctk.set_appearance_mode(new_mode)
            ctk.AppearanceModeTracker.update_callbacks()

    def _on_language_changed(self, new_locale: str) -> None:
        """Applies language change dynamically across all UI components without app restart."""
        self.config_mgr.language = new_locale
        i18n.init(new_locale)
        self.title(i18n.t("app_title"))
        self.toolbar.refresh_ui_texts()
        self.preview_panel.refresh_ui_texts()
        self.export_panel.refresh_ui_texts()

    def _on_delay_changed(self, new_delay: int) -> None:
        """Updates capture delay in persistent configuration and running browser manager."""
        self.config_mgr.capture_delay = new_delay
        self.browser_mgr.capture_delay = float(new_delay)

    def _on_list_updated(self) -> None:
        """Invoked when screenshots list or order changes."""
        self.export_panel.update_states()

    # ------------------ Browser Event Callbacks ------------------

    def _handle_browser_started_event(self) -> None:
        self.after(0, lambda: self.toolbar.set_browser_running(True))

    def _handle_browser_closed_event(self) -> None:
        # Prompt in status bar and restore launch button for one-click relaunch
        self.after(0, lambda: self.toolbar.set_browser_running(False, was_closed=True))

    def _handle_page_title_event(self, title: str, url: str) -> None:
        self.after(0, lambda: self.toolbar.set_active_page_info(title, url))

    def _handle_tabs_updated_event(self, tabs: list[dict], active_index: int) -> None:
        self.after(0, lambda: self.toolbar.update_tabs_list(tabs, active_index))

    def _handle_range_start_ready_event(self, start_y: int) -> None:
        self.after(0, lambda: self.toolbar.set_range_mode(True, start_y))

    def _on_tab_selected(self, tab_index: int) -> None:
        """User selected a tab from the Dropdown list."""
        self.browser_mgr.switch_tab(tab_index)

    def _handle_screenshot_event(
        self, img_bytes: bytes, title: str, url: str, full_page: bool
    ) -> None:
        def on_ui_thread() -> None:
            self._hide_loading()
            # Save screenshot to temporary file
            idx = self.model.count() + 1
            filename = f"snap_{int(time.time() * 1000)}_{idx}.png"
            path = file_utils.save_screenshot_bytes(img_bytes, filename)
            thumb = image_utils.bytes_to_thumbnail(img_bytes)

            shot = Screenshot(
                filepath=path,
                label=f"#{idx:02d} {title}",
                thumbnail=thumb,
                page_title=title,
                page_url=url,
                is_full_page=full_page,
            )
            self.model.add(shot)
            self.preview_panel.refresh_list(select_index=self.model.count() - 1)
            self.export_panel.update_states()

        self.after(0, on_ui_thread)

    def _handle_browser_error_event(self, err_msg: str) -> None:
        def on_ui_thread() -> None:
            self._hide_loading()
            messagebox.showerror(i18n.t("app_title"), f"Browser Error: {err_msg}")

        self.after(0, on_ui_thread)

    # ------------------ Window Lifecycle ------------------

    def _on_window_close(self) -> None:
        """Handles application shutdown and temp cleanup."""
        # Check if unsaved screenshots exist
        if self.model.has_unsaved:
            dialog = UnsavedChangesDialog(self, unsaved_count=self.model.count())
            self.wait_window(dialog)
            if not dialog.result:
                # User cancelled quitting
                return

        # Show closing loading dialog and ensure UI is rendered
        self._show_loading(i18n.t("loading_closing"))
        self.update()

        # Cleanly shut down browser and close Playwright IPC pipe
        if self.browser_mgr.is_running:
            self.browser_mgr.close(wait=True)

        # Clean temporary screenshot folder
        try:
            file_utils.cleanup_temp_dir()
        except Exception:
            pass

        self._hide_loading()
        self.destroy()

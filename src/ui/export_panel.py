"""Bottom export panel component for SnapFlow."""

from __future__ import annotations

from pathlib import Path
from tkinter import filedialog, messagebox
from typing import Callable
import customtkinter as ctk
from config_manager import ConfigManager
from i18n import t
from screenshot_model import ScreenshotModel
from utils import image_utils


class ExportPanel(ctk.CTkFrame):
    """Panel providing PNG batch export and single PDF compilation."""

    def __init__(
        self,
        master: ctk.CTk,
        model: ScreenshotModel,
        config_mgr: ConfigManager,
        get_selected_indices: Callable[[], list[int]] | None = None,
        on_export_success: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__(master, corner_radius=0)
        self.model = model
        self.config_mgr = config_mgr
        self.get_selected_indices = get_selected_indices
        self.on_export_success = on_export_success
        self._toast_timer_id = None
        self._is_updating_menu = False

        self._build_ui()
        self.update_states()

    def _build_ui(self) -> None:
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(fill="x", padx=16, pady=10)

        # Left status / count / toast notification
        self.lbl_count = ctk.CTkLabel(
            container,
            text=t("status_bar_count", count=0),
            font=ctk.CTkFont(size=13),
            text_color=("gray40", "gray70"),
        )
        self.lbl_count.pack(side="left")

        # Right export dropdown menu
        self.export_var = ctk.StringVar(value=t("btn_export_menu"))
        self.export_menu = ctk.CTkOptionMenu(
            container,
            values=[t("btn_export_menu")],
            variable=self.export_var,
            command=self._handle_export_menu_action,
            font=ctk.CTkFont(size=13, weight="bold"),
            dropdown_font=ctk.CTkFont(size=12),
            fg_color="#2E7D32",
            button_color="#1B5E20",
            button_hover_color="#0E3A13",
            width=230,
            height=36,
        )
        self.export_menu.pack(side="right")

    def show_toast(self, message: str, duration_ms: int = 4000) -> None:
        """Displays a non-blocking toast message in the status bar and reverts after duration."""
        if self._toast_timer_id:
            try:
                self.after_cancel(self._toast_timer_id)
            except Exception:
                pass
            self._toast_timer_id = None

        self.lbl_count.configure(
            text=f"✓ {message}",
            text_color=("#2E7D32", "#4CAF50"),
        )
        self._toast_timer_id = self.after(duration_ms, self._revert_toast)

    def _revert_toast(self) -> None:
        """Restores normal status bar count text."""
        self._toast_timer_id = None
        count = self.model.count()
        self.lbl_count.configure(
            text=t("status_bar_count", count=count),
            text_color=("gray40", "gray70"),
        )

    def update_states(self) -> None:
        """Enables/disables and updates export dropdown menu options depending on count and selection."""
        count = self.model.count()
        if not self._toast_timer_id:
            self.lbl_count.configure(text=t("status_bar_count", count=count))

        state = "normal" if count > 0 else "disabled"
        self.export_menu.configure(state=state)

        sel_indices = self.get_selected_indices() if self.get_selected_indices else []
        sel_count = len(sel_indices)

        # Build dropdown options dynamically
        self._menu_options = [
            t("export_all_png"),
            t("export_all_pdf"),
        ]

        # If user has a selection (even 1 item counts as a selection), add Selected export options
        if 0 < sel_count:
            self._menu_options.insert(0, t("export_selected_pdf", count=sel_count))
            self._menu_options.insert(0, t("export_selected_png", count=sel_count))

        self._is_updating_menu = True
        try:
            self.export_menu.configure(values=self._menu_options)
            self.export_var.set(t("btn_export_menu"))
        finally:
            self._is_updating_menu = False

    def refresh_ui_texts(self) -> None:
        """Dynamically refreshes all label and menu texts according to active locale."""
        if not self._toast_timer_id:
            self.lbl_count.configure(text=t("status_bar_count", count=self.model.count()))
        self.update_states()

    def _handle_export_menu_action(self, choice: str) -> None:
        """Dispatches action chosen from Export Dropdown Menu."""
        if self._is_updating_menu or not choice:
            return

        sel_indices = self.get_selected_indices() if self.get_selected_indices else []
        sel_count = len(sel_indices)

        # Always reset dropdown title back to "💾 Export / Save"
        self.export_var.set(t("btn_export_menu"))

        opt_sel_png = t("export_selected_png", count=sel_count) if sel_count > 0 else None
        opt_sel_pdf = t("export_selected_pdf", count=sel_count) if sel_count > 0 else None

        if choice == opt_sel_png:
            self._export_pngs(only_selected=True)
        elif choice == opt_sel_pdf:
            self._export_pdf(only_selected=True)
        elif choice == t("export_all_png"):
            self._export_pngs(only_selected=False)
        elif choice == t("export_all_pdf"):
            self._export_pdf(only_selected=False)

    def _export_pngs(self, only_selected: bool) -> None:
        if only_selected:
            sel_indices = self.get_selected_indices() if self.get_selected_indices else []
            target_shots = self.model.get_shots(sel_indices)
        else:
            target_shots = self.model.shots

        if not target_shots:
            messagebox.showwarning(t("app_title"), t("error_no_screenshots"))
            return

        initial_dir = self.config_mgr.last_png_dir or str(Path.home())
        dest_dir = filedialog.askdirectory(
            title=t("dialog_save_dir"),
            initialdir=initial_dir,
        )
        if not dest_dir:
            return

        self.config_mgr.last_png_dir = dest_dir

        try:
            saved = image_utils.export_pngs(target_shots, dest_dir)
            self.model.mark_exported()
            msg = t("toast_export_png_done", count=len(saved), path=dest_dir)
            if self.on_export_success:
                self.on_export_success(msg)
            self.show_toast(msg)
        except Exception as e:
            messagebox.showerror(t("app_title"), f"Failed to save PNGs: {e}")

    def _export_pdf(self, only_selected: bool) -> None:
        if only_selected:
            sel_indices = self.get_selected_indices() if self.get_selected_indices else []
            target_shots = self.model.get_shots(sel_indices)
        else:
            target_shots = self.model.shots

        filepaths = [s.filepath for s in target_shots if s.filepath and s.filepath.exists()]
        if not filepaths:
            messagebox.showwarning(t("app_title"), t("error_no_screenshots"))
            return

        initial_dir = self.config_mgr.last_pdf_dir or str(Path.home())
        out_path = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF Document", "*.pdf")],
            title=t("dialog_save_pdf"),
            initialdir=initial_dir,
            initialfile="SnapFlow_Export.pdf",
        )
        if not out_path:
            return

        self.config_mgr.last_pdf_dir = str(Path(out_path).parent)

        # Pre-check if target file is writable (e.g. not locked by Adobe Reader or another process)
        target_path = Path(out_path)
        if target_path.exists():
            try:
                with open(target_path, "a+"):
                    pass
            except (PermissionError, OSError):
                messagebox.showerror(t("app_title"), t("error_file_locked"))
                return

        try:
            image_utils.export_pdf(filepaths, out_path)
            self.model.mark_exported()
            msg = t("toast_export_pdf_done", path=out_path)
            if self.on_export_success:
                self.on_export_success(msg)
            self.show_toast(msg)
        except PermissionError:
            messagebox.showerror(t("app_title"), t("error_file_locked"))
        except Exception as e:
            messagebox.showerror(t("app_title"), f"Failed to export PDF: {e}")

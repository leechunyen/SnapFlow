"""Custom modal dialogs for SnapFlow."""

from __future__ import annotations

from typing import Callable
import customtkinter as ctk
from i18n import t


class UnsavedChangesDialog(ctk.CTkToplevel):
    """Confirmation dialog shown when quitting with unexported screenshots."""

    def __init__(self, parent: ctk.CTk, unsaved_count: int) -> None:
        super().__init__(parent)
        self.result: bool = False  # True = Quit, False = Cancel

        self.title(t("dialog_unsaved_title"))
        self.geometry("440x210")
        self.resizable(False, False)

        # Modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent window
        parent.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        cx = px + (pw - 440) // 2
        cy = py + (ph - 210) // 2
        self.geometry(f"+{cx}+{cy}")

        self._build_ui(unsaved_count)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self, count: int) -> None:
        main_frame = ctk.CTkFrame(self, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        # Warning icon & title header
        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(16, 8))

        icon_label = ctk.CTkLabel(
            header_frame,
            text="⚠️",
            font=ctk.CTkFont(size=26),
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text=t("dialog_unsaved_title"),
            font=ctk.CTkFont(size=18, weight="bold"),
        )
        title_label.pack(side="left")

        # Message body
        msg_text = t("dialog_unsaved_msg", count=count)
        msg_label = ctk.CTkLabel(
            main_frame,
            text=msg_text,
            font=ctk.CTkFont(size=14),
            justify="left",
            wraplength=380,
        )
        msg_label.pack(fill="x", padx=16, pady=(0, 16))

        # Buttons frame
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 8))

        cancel_btn = ctk.CTkButton(
            btn_frame,
            text=t("dialog_unsaved_cancel"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            width=110,
            command=self._on_cancel,
        )
        cancel_btn.pack(side="right", padx=(8, 0))

        quit_btn = ctk.CTkButton(
            btn_frame,
            text=t("dialog_unsaved_quit"),
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            width=130,
            command=self._on_quit,
        )
        quit_btn.pack(side="right")

    def _on_quit(self) -> None:
        self.result = True
        self.grab_release()
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = False
        self.grab_release()
        self.destroy()


class RenameDialog(ctk.CTkToplevel):
    """Modal dialog for renaming screenshots with real-time duplication validation."""

    def __init__(
        self,
        parent: ctk.CTk,
        current_name: str,
        validator: Callable[[str], tuple[bool, str]],
    ) -> None:
        super().__init__(parent)
        self.result: str | None = None
        self.validator = validator

        self.title(t("dialog_rename_title"))
        self.geometry("480x240")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        cx = px + (pw - 480) // 2
        cy = py + (ph - 240) // 2
        self.geometry(f"+{cx}+{cy}")

        self._build_ui(current_name)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self, current_name: str) -> None:
        main_frame = ctk.CTkFrame(self, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        header_label = ctk.CTkLabel(
            main_frame,
            text=f"✏️ {t('dialog_rename_title')}",
            font=ctk.CTkFont(size=16, weight="bold"),
        )
        header_label.pack(anchor="w", padx=16, pady=(12, 4))

        hint_label = ctk.CTkLabel(
            main_frame,
            text=t("dialog_rename_hint"),
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "gray70"),
        )
        hint_label.pack(anchor="w", padx=16, pady=(0, 8))

        self.entry_var = ctk.StringVar(value=current_name)
        self.entry = ctk.CTkEntry(
            main_frame,
            textvariable=self.entry_var,
            font=ctk.CTkFont(size=14),
            height=36,
        )
        self.entry.pack(fill="x", padx=16, pady=(0, 4))
        self.entry.focus_set()
        self.entry.select_range(0, "end")
        self.entry.bind("<Return>", lambda e: self._on_confirm())
        self.entry.bind("<KeyRelease>", lambda e: self._validate_input_realtime())

        # Error message label
        self.lbl_error = ctk.CTkLabel(
            main_frame,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#D32F2F",
            anchor="w",
        )
        self.lbl_error.pack(fill="x", padx=16, pady=(0, 8))

        # Button row
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(4, 8))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text=t("dialog_rename_cancel"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            width=100,
            command=self._on_cancel,
        )
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_confirm = ctk.CTkButton(
            btn_frame,
            text=t("dialog_rename_confirm"),
            width=100,
            command=self._on_confirm,
        )
        btn_confirm.pack(side="right")

    def _validate_input_realtime(self) -> None:
        """Immediately checks typed characters and surfaces warnings for invalid filename characters."""
        import re
        val = self.entry_var.get()
        if re.search(r'[\\/*?:"<>|]', val):
            self.lbl_error.configure(text=t("error_invalid_chars"))
        else:
            self.lbl_error.configure(text="")

    def _on_confirm(self) -> None:
        import re
        name = self.entry_var.get().strip()
        if not name:
            self.lbl_error.configure(text=t("error_empty_name"))
            self.entry.focus_set()
            return

        if re.search(r'[\\/*?:"<>|]', name):
            self.lbl_error.configure(text=t("error_invalid_chars"))
            self.entry.focus_set()
            self.bell()
            return

        is_valid, err_msg = self.validator(name)
        if not is_valid:
            # Block rename and show warning message
            self.lbl_error.configure(text=err_msg)
            self.entry.focus_set()
            self.entry.select_range(0, "end")
            self.bell()
            return

        self.result = name
        self.grab_release()
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = None
        self.grab_release()
        self.destroy()


class ConfirmDeleteDialog(ctk.CTkToplevel):
    """Confirmation modal dialog when deleting a screenshot."""

    def __init__(self, parent: ctk.CTk, item_name: str = "", count: int = 1) -> None:
        super().__init__(parent)
        self.result: bool = False

        self.title(t("dialog_delete_title"))
        self.geometry("420x200")
        self.resizable(False, False)

        self.transient(parent)
        self.grab_set()

        parent.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        cx = px + (pw - 420) // 2
        cy = py + (ph - 200) // 2
        self.geometry(f"+{cx}+{cy}")

        self._build_ui(item_name, count)
        self.protocol("WM_DELETE_WINDOW", self._on_cancel)

    def _build_ui(self, item_name: str, count: int) -> None:
        main_frame = ctk.CTkFrame(self, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=16, pady=16)

        header_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        header_frame.pack(fill="x", padx=16, pady=(14, 8))

        icon_label = ctk.CTkLabel(
            header_frame,
            text="🗑",
            font=ctk.CTkFont(size=24),
        )
        icon_label.pack(side="left", padx=(0, 10))

        title_label = ctk.CTkLabel(
            header_frame,
            text=t("dialog_delete_title"),
            font=ctk.CTkFont(size=17, weight="bold"),
        )
        title_label.pack(side="left")

        # Message body
        if count > 1:
            msg_text = t("dialog_delete_confirm_multi", count=count)
        else:
            msg_text = t("dialog_delete_confirm")
            if item_name:
                msg_text = f"{msg_text}\n({item_name})"
        msg_label = ctk.CTkLabel(
            main_frame,
            text=msg_text,
            font=ctk.CTkFont(size=13),
            justify="left",
            wraplength=360,
        )
        msg_label.pack(fill="x", padx=16, pady=(0, 16))

        # Buttons frame
        btn_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=16, pady=(0, 8))

        btn_cancel = ctk.CTkButton(
            btn_frame,
            text=t("dialog_rename_cancel"),
            fg_color="transparent",
            border_width=1,
            text_color=("gray10", "gray90"),
            hover_color=("gray85", "gray25"),
            width=100,
            command=self._on_cancel,
        )
        btn_cancel.pack(side="right", padx=(8, 0))

        btn_confirm = ctk.CTkButton(
            btn_frame,
            text=t("btn_delete"),
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            width=100,
            command=self._on_confirm,
        )
        btn_confirm.pack(side="right")

    def _on_confirm(self) -> None:
        self.result = True
        self.grab_release()
        self.destroy()

    def _on_cancel(self) -> None:
        self.result = False
        self.grab_release()
        self.destroy()


class LoadingDialog(ctk.CTkToplevel):
    """Modal overlay that displays an animated loading bar and blocks user input during long operations."""

    def __init__(self, parent: ctk.CTk, message: str) -> None:
        super().__init__(parent)
        self.title("")
        self.geometry("380x130")
        self.resizable(False, False)

        # Remove window decoration if supported and ensure modal behavior
        self.transient(parent)
        self.grab_set()

        # Center on parent window
        parent.update_idletasks()
        pw = parent.winfo_width()
        ph = parent.winfo_height()
        px = parent.winfo_x()
        py = parent.winfo_y()
        cx = px + (pw - 380) // 2
        cy = py + (ph - 130) // 2
        self.geometry(f"+{cx}+{cy}")

        main_frame = ctk.CTkFrame(self, corner_radius=12)
        main_frame.pack(fill="both", expand=True, padx=12, pady=12)

        self.lbl_msg = ctk.CTkLabel(
            main_frame,
            text=message,
            font=ctk.CTkFont(size=14, weight="bold"),
        )
        self.lbl_msg.pack(pady=(16, 12), padx=16)

        self.progressbar = ctk.CTkProgressBar(main_frame, mode="indeterminate", width=300)
        self.progressbar.pack(pady=(0, 16), padx=20)
        self.progressbar.start()

        # Prevent closing via Alt+F4 or window manager
        self.protocol("WM_DELETE_WINDOW", lambda: None)

    def close(self) -> None:
        """Safely dismisses the loading modal dialog."""
        try:
            self.progressbar.stop()
            self.grab_release()
            self.destroy()
        except Exception:
            pass


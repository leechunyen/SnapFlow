"""Preview panel component for SnapFlow.

Displays screenshot thumbnails, metadata, and re-orderable item list with
drag-and-drop, up/down/rename/delete actions.
"""

from __future__ import annotations

import tkinter as tk
import tkinter.font as tkfont
from typing import Callable
import customtkinter as ctk
from PIL import Image

Image.MAX_IMAGE_PIXELS = None
from i18n import t
from screenshot_model import Screenshot, ScreenshotModel
from ui.dialogs import ConfirmDeleteDialog, RenameDialog


class DragDropListbox(tk.Listbox):
    """Tkinter Listbox supporting multi-selection and clean keyboard/button navigation."""

    def __init__(
        self,
        master: tk.Widget,
        on_reorder: Callable[[int, int], None] | None = None,
        on_select: Callable[[int], None] | None = None,
        **kwargs,
    ) -> None:
        super().__init__(master, **kwargs)
        self.on_reorder = on_reorder
        self.on_select = on_select

        self.bind("<Command-Button-1>", self._on_cmd_press)
        self.bind("<Control-Button-1>", self._on_ctrl_press)
        self.bind("<<ListboxSelect>>", self._on_listbox_select)

    def _toggle_item(self, idx: int) -> None:
        if 0 <= idx < self.size():
            if self.selection_includes(idx):
                self.selection_clear(idx)
            else:
                self.selection_set(idx)
                self.activate(idx)
            self._on_listbox_select(None)

    def _on_cmd_press(self, event: tk.Event) -> str | None:
        """macOS: CMD-click toggles selection. Win/Linux: ignored."""
        import sys
        if sys.platform == "darwin":
            idx = self.nearest(event.y)
            self._toggle_item(idx)
            return "break"
        return None

    def _on_ctrl_press(self, event: tk.Event) -> str | None:
        """Win/Linux: CTRL-click toggles selection. macOS: pass through for native context menu handling."""
        import sys
        if sys.platform != "darwin":
            idx = self.nearest(event.y)
            self._toggle_item(idx)
            return "break"
        # On macOS, Control-Button-1 is conventionally secondary/right-click.
        return None

    def _on_listbox_select(self, event: tk.Event | None = None) -> None:
        if self.on_select:
            sel = self.curselection()
            if len(sel) == 1:
                self.on_select(sel[0])
            else:
                # Multiple items selected or no selection: clear preview
                self.on_select(-1)


class PreviewPanel(ctk.CTkFrame):
    """Container holding list of captures (with reordering) and preview card."""

    def __init__(
        self,
        master: ctk.CTk,
        model: ScreenshotModel,
        on_list_changed: Callable[[], None] | None = None,
    ) -> None:
        super().__init__(master, corner_radius=12)
        self.model = model
        self.on_list_changed = on_list_changed
        self._selected_index: int | None = None
        self._ctk_image: ctk.CTkImage | None = None
        self._copy_timer: str | None = None
        self._resize_timer: str | None = None

        self._build_ui()
        self.update_theme_colors(ctk.get_appearance_mode())
        self.refresh_list()

    def _build_ui(self) -> None:
        # Left column expands (weight=1), Right preview column fixed width (weight=0)
        self.grid_columnconfigure(0, weight=1, minsize=380)
        self.grid_columnconfigure(1, weight=0, minsize=520)
        self.grid_rowconfigure(0, weight=1)

        # ----------------- Left column: List and Controls -----------------
        left_card = ctk.CTkFrame(self, corner_radius=10)
        left_card.grid(row=0, column=0, sticky="nsew", padx=(12, 6), pady=12)
        left_card.grid_rowconfigure(1, weight=1)
        left_card.grid_columnconfigure(0, weight=1)

        # List Header
        self.lbl_list_title = ctk.CTkLabel(
            left_card,
            text=f"📋 {t('label_screenshots')}",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        )
        self.lbl_list_title.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))

        # Listbox container with scrollbar
        list_container = ctk.CTkFrame(left_card, fg_color="transparent")
        list_container.grid(row=1, column=0, sticky="nsew", padx=12, pady=(0, 8))
        list_container.grid_rowconfigure(0, weight=1)
        list_container.grid_columnconfigure(0, weight=1)

        self._listbox_font = ("Segoe UI" if tk.TkVersion >= 8.6 else "Helvetica", 12)
        self.listbox = DragDropListbox(
            list_container,
            on_reorder=self._handle_reorder,
            on_select=self._handle_select,
            font=self._listbox_font,
            selectmode=tk.EXTENDED,
            exportselection=False,
            activestyle="none",
            borderwidth=0,
            highlightthickness=1,
        )
        self.listbox.grid(row=0, column=0, sticky="nsew")
        self.listbox.bind("<Configure>", self._on_listbox_resize)

        scrollbar = ctk.CTkScrollbar(list_container, command=self.listbox.yview)
        scrollbar.grid(row=0, column=1, sticky="ns")
        self.listbox.configure(yscrollcommand=scrollbar.set)

        # Empty state placeholder label over the listbox
        self.lbl_empty_list = ctk.CTkLabel(
            list_container,
            text=f"📂 {t('label_no_screenshots')}",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
        )

        # Action buttons row: [▲ Up] [▼ Down] [✏️ Rename] [🗑 Delete]
        btn_bar = ctk.CTkFrame(left_card, fg_color="transparent")
        btn_bar.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 12))

        self.btn_up = ctk.CTkButton(
            btn_bar,
            text=t("btn_move_up"),
            width=80,
            height=30,
            command=self._handle_move_up,
        )
        self.btn_up.pack(side="left", padx=(0, 6))

        self.btn_down = ctk.CTkButton(
            btn_bar,
            text=t("btn_move_down"),
            width=80,
            height=30,
            command=self._handle_move_down,
        )
        self.btn_down.pack(side="left", padx=(0, 6))

        self.btn_rename = ctk.CTkButton(
            btn_bar,
            text=t("btn_rename"),
            width=100,
            height=30,
            command=self._handle_rename,
            fg_color="#455A64",
            hover_color="#37474F",
        )
        self.btn_rename.pack(side="left")

        self.btn_delete = ctk.CTkButton(
            btn_bar,
            text=t("btn_delete"),
            fg_color="#D32F2F",
            hover_color="#B71C1C",
            width=85,
            height=30,
            command=self._handle_delete,
        )
        self.btn_delete.pack(side="right")

        # ----------------- Right column: Fixed Preview Display -----------------
        right_card = ctk.CTkFrame(self, width=500, corner_radius=10)
        right_card.grid(row=0, column=1, sticky="ns", padx=(6, 12), pady=12)
        right_card.grid_propagate(False)
        right_card.grid_rowconfigure(1, weight=1)
        right_card.grid_columnconfigure(0, weight=1)

        # Preview Header
        self.lbl_preview_title = ctk.CTkLabel(
            right_card,
            text=f"🖼 {t('label_preview')}",
            font=ctk.CTkFont(size=15, weight="bold"),
            anchor="w",
        )
        self.lbl_preview_title.grid(row=0, column=0, sticky="ew", padx=14, pady=(12, 8))

        # Scrollable image view area (填滿寬度並支援上下捲動)
        self.image_container = ctk.CTkScrollableFrame(
            right_card,
            corner_radius=8,
            fg_color=("gray90", "#212121"),
        )
        self.image_container.grid(row=1, column=0, sticky="nsew", padx=14, pady=(0, 10))

        # Empty state placeholder label for preview area (parented to right_card and placed in _parent_canvas of scroll frame for exact centering)
        self.lbl_empty_preview = ctk.CTkLabel(
            right_card,
            text=f"📂 {t('label_no_screenshots')}",
            font=ctk.CTkFont(size=13),
            text_color=("gray50", "gray60"),
            fg_color=("gray90", "#212121"),
        )
        self.lbl_empty_preview.place(in_=self.image_container._parent_canvas, relx=0.5, rely=0.5, anchor="center")

        self.lbl_image_display = ctk.CTkLabel(
            self.image_container,
            text="",
            font=ctk.CTkFont(size=14),
        )
        self.lbl_image_display.pack(expand=True, fill="both", padx=4, pady=4)

        # Metadata info labels
        self.info_box = ctk.CTkFrame(right_card, fg_color="transparent")
        self.info_box.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))

        self.lbl_meta_title = ctk.CTkLabel(
            self.info_box,
            text="",
            font=ctk.CTkFont(size=13, weight="bold"),
            anchor="w",
            wraplength=480,
        )
        self.lbl_meta_title.pack(fill="x")

        # URL row with truncated display and quick Copy button
        self.url_frame = ctk.CTkFrame(self.info_box, fg_color="transparent")
        self.url_frame.pack(fill="x", pady=(2, 0))

        self.lbl_meta_url = ctk.CTkLabel(
            self.url_frame,
            text="",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray65"),
            anchor="w",
            cursor="hand2",
        )
        self.lbl_meta_url.pack(side="left", fill="x", expand=True)
        self.lbl_meta_url.bind("<Button-1>", lambda e: self._copy_current_url())

        self.btn_copy_url = ctk.CTkButton(
            self.url_frame,
            text=t("btn_copy_url"),
            font=ctk.CTkFont(size=11),
            width=70,
            height=24,
            fg_color=("gray75", "gray30"),
            text_color=("gray10", "gray95"),
            hover_color=("gray65", "gray40"),
            command=self._copy_current_url,
        )
        self._current_full_url: str = ""

    def update_theme_colors(self, appearance_mode: str | int) -> None:
        """Adapts Listbox appearance to the current theme."""
        if isinstance(appearance_mode, int):
            is_dark = appearance_mode == 1
        else:
            is_dark = str(appearance_mode).strip().lower() == "dark"

        if is_dark:
            self.listbox.configure(
                bg="#23272D",
                fg="#F0F0F0",
                selectbackground="#1F6AA5",
                selectforeground="#FFFFFF",
                highlightbackground="#343A40",
                highlightcolor="#1F6AA5",
            )
            self.lbl_empty_list.configure(fg_color="#23272D", text_color="#8A94A6")
            self.lbl_empty_preview.configure(fg_color="#212121", text_color="#8A94A6")
        else:
            self.listbox.configure(
                bg="#FFFFFF",
                fg="#1A1A1A",
                selectbackground="#3B8ED0",
                selectforeground="#FFFFFF",
                highlightbackground="#D1D5DB",
                highlightcolor="#3B8ED0",
            )
            self.lbl_empty_list.configure(fg_color="#FFFFFF", text_color="#718096")
            self.lbl_empty_preview.configure(fg_color="gray90", text_color="#718096")

    def refresh_ui_texts(self) -> None:
        """Dynamically refreshes all label and button texts according to active locale."""
        self.lbl_list_title.configure(text=f"📋 {t('label_screenshots')}")
        self.lbl_preview_title.configure(text=f"🖼 {t('label_preview')}")
        self.btn_up.configure(text=t("btn_move_up"))
        self.btn_down.configure(text=t("btn_move_down"))
        self.btn_rename.configure(text=t("btn_rename"))
        self.btn_delete.configure(text=t("btn_delete"))
        self.btn_copy_url.configure(text=t("btn_copy_url"))
        self.lbl_empty_list.configure(text=f"📂 {t('label_no_screenshots')}")
        self.lbl_empty_preview.configure(text=f"📂 {t('label_no_screenshots')}")

        # Re-render list and active item preview metadata
        self.refresh_list(select_index=self._selected_index)

    def _on_listbox_resize(self, event: tk.Event) -> None:
        """Called when Listbox dimensions change (e.g. window resize). Updates text formatting to fill width."""
        if hasattr(self, "_last_listbox_width") and abs(self._last_listbox_width - event.width) < 5:
            return
        self._last_listbox_width = event.width
        # Debounce item texts update if we have items
        if self.model.count() > 0:
            if self._resize_timer is not None:
                try:
                    self.after_cancel(self._resize_timer)
                except Exception:
                    pass
            self._resize_timer = self.after(80, self._update_list_display_texts)

    def _format_item_text(self, idx: int, shot: Screenshot, available_px: int, font: tkfont.Font) -> str:
        """Dynamically fits the screenshot item string into the available pixel width."""
        tag = "[Full]" if shot.is_full_page else "[View]"
        prefix = f"#{idx:02d}  {tag} "
        name_to_display = shot.custom_name if shot.custom_name else (shot.page_title or "Untitled")

        full_text = f"{prefix}{name_to_display}"
        # If the full text comfortably fits, display it completely
        if font.measure(full_text) <= available_px:
            return full_text

        # Otherwise truncate name with '...' to fill the exact available width
        ellipsis = "..."
        prefix_ellipsis_w = font.measure(f"{prefix}{ellipsis}")
        max_name_px = available_px - prefix_ellipsis_w

        if max_name_px <= 0:
            return f"{prefix}{name_to_display[:10]}..."

        # Binary or linear chop to find the maximum substring that fits
        low, high = 1, len(name_to_display)
        best_str = name_to_display[:1]
        while low <= high:
            mid = (low + high) // 2
            candidate = name_to_display[:mid]
            if font.measure(candidate) <= max_name_px:
                best_str = candidate
                low = mid + 1
            else:
                high = mid - 1

        return f"{prefix}{best_str}{ellipsis}"

    def _update_list_display_texts(self) -> None:
        """Refreshes text of existing items in the Listbox without changing selection or scrolling."""
        if self.model.count() == 0:
            return

        font = tkfont.Font(font=self.listbox.cget("font"))
        # Usable width in pixels (minus padding, border, and selection margin ~25px)
        usable_w = max(180, self.listbox.winfo_width() - 25)

        # Preserve selection
        current_selection = self.listbox.curselection()
        y_view = self.listbox.yview()

        self.listbox.delete(0, tk.END)
        for idx, shot in enumerate(self.model.shots, start=1):
            item_text = self._format_item_text(idx, shot, usable_w, font)
            self.listbox.insert(tk.END, item_text)

        # Restore selection and scroll position
        for sel_idx in current_selection:
            self.listbox.selection_set(sel_idx)
        try:
            self.listbox.yview_moveto(y_view[0])
        except Exception:
            pass

    def refresh_list(self, select_index: int | None = None) -> None:
        """Re-populates the listbox items from ScreenshotModel adapting to available space."""
        self.listbox.delete(0, tk.END)

        font = tkfont.Font(font=self.listbox.cget("font"))
        usable_w = max(180, self.listbox.winfo_width() - 25)

        for idx, shot in enumerate(self.model.shots, start=1):
            item_text = self._format_item_text(idx, shot, usable_w, font)
            self.listbox.insert(tk.END, item_text)

        count = self.model.count()
        if count > 0:
            self.lbl_empty_list.place_forget()
            if select_index is not None and 0 <= select_index < count:
                idx_to_select = select_index
            elif self._selected_index is not None and 0 <= self._selected_index < count:
                idx_to_select = self._selected_index
            else:
                idx_to_select = count - 1  # Select newest item by default

            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx_to_select)
            self.listbox.activate(idx_to_select)
            self.listbox.see(idx_to_select)
            self._handle_select(idx_to_select)
        else:
            self._selected_index = None
            self.lbl_empty_list.place(relx=0.5, rely=0.5, anchor="center")
            self._clear_preview()

        if self.on_list_changed:
            self.on_list_changed()
        self._update_action_buttons()

    def _update_action_buttons(self) -> None:
        """Disables Rename and Move Up/Down buttons when multiple items are selected or list is empty."""
        selected_count = len(self.get_selected_indices())
        if selected_count == 1:
            self.btn_up.configure(state="normal")
            self.btn_down.configure(state="normal")
            self.btn_rename.configure(state="normal")
        else:
            self.btn_up.configure(state="disabled")
            self.btn_down.configure(state="disabled")
            self.btn_rename.configure(state="disabled")

        if selected_count > 0:
            self.btn_delete.configure(state="normal")
        else:
            self.btn_delete.configure(state="disabled")

    def _handle_select(self, index: int) -> None:
        if 0 <= index < len(self.model.shots):
            self._selected_index = index
            shot = self.model.shots[index]
            self._show_preview(shot)
        else:
            self._selected_index = None
            self._clear_preview()

        if self.on_list_changed:
            self.on_list_changed()
        self._update_action_buttons()

    def _show_preview(self, shot: Screenshot) -> None:
        """Renders the selected screenshot to fill the preview container width, allowing smooth vertical scrolling."""
        if shot.filepath and shot.filepath.exists():
            try:
                # Fill container width (card width is 500px, scrollable inner width is ~440px)
                target_w = 440

                with Image.open(shot.filepath) as full_img:
                    w, h = full_img.size
                    scale = target_w / w if w > 0 else 1.0
                    thumb_w = target_w
                    thumb_h = max(1, int(h * scale))
                    thumb_size = (thumb_w, thumb_h)

                    resized = full_img.resize(thumb_size, Image.Resampling.LANCZOS)
                    self._ctk_image = ctk.CTkImage(
                        light_image=resized,
                        dark_image=resized,
                        size=thumb_size,
                    )

                try:
                    self.lbl_image_display._label.configure(image="")
                except Exception:
                    pass

                self.lbl_empty_preview.place_forget()
                self.lbl_image_display.configure(
                    image=self._ctk_image,
                    text="",
                )

                # Reset scrollbar to the very top when switching to a new screenshot
                try:
                    self.image_container._parent_canvas.yview_moveto(0.0)
                except Exception:
                    pass

                type_str = t("btn_screenshot_fullpage") if shot.is_full_page else t("btn_screenshot_viewport")
                display_name = f"[{shot.custom_name}] " if shot.custom_name else ""
                self.lbl_meta_title.configure(
                    text=f"{type_str}: {display_name}{shot.page_title or 'Untitled'} ({w}x{h} px)"
                )

                self._current_full_url = shot.page_url or ""
                if self._current_full_url:
                    truncated = self._current_full_url
                    if len(truncated) > 65:
                        truncated = truncated[:62] + "..."
                    self.lbl_meta_url.configure(text=f"🔗 {truncated}")
                    self.btn_copy_url.pack(side="right", padx=(8, 0))
                else:
                    self.lbl_meta_url.configure(text="")
                    self.btn_copy_url.pack_forget()
                return
            except Exception as e:
                print(f"[PreviewPanel] Preview error: {e}")

        self._clear_preview()

    def _clear_preview(self) -> None:
        self._ctk_image = None
        self._current_full_url = ""
        try:
            self.lbl_image_display._label.configure(image="")
        except Exception:
            pass
        try:
            self.lbl_image_display.configure(
                image=None,
                text="",
            )
        except Exception:
            pass
        self.lbl_empty_preview.place(in_=self.image_container._parent_canvas, relx=0.5, rely=0.5, anchor="center")
        self.lbl_meta_title.configure(text="")
        self.lbl_meta_url.configure(text="")
        self.btn_copy_url.pack_forget()

    def _copy_current_url(self) -> None:
        """Copies the full active page URL to system clipboard."""
        if not self._current_full_url:
            return
        self.clipboard_clear()
        self.clipboard_append(self._current_full_url)
        self.update()

        # Cancel previous timer if active to prevent race condition
        if self._copy_timer:
            try:
                self.after_cancel(self._copy_timer)
            except Exception:
                pass
            self._copy_timer = None

        # Temporary button text feedback
        orig_text = f"📋 {t('btn_copy_url')}"
        self.btn_copy_url.configure(text="✓ Copied!")

        def reset_copy_btn():
            self._copy_timer = None
            try:
                self.btn_copy_url.configure(text=orig_text)
            except Exception:
                pass

        self._copy_timer = self.after(1500, reset_copy_btn)

    def get_selected_indices(self) -> list[int]:
        """Returns all currently selected indices, or [active_index] if fallback."""
        sel = self.listbox.curselection()
        if sel:
            return list(sel)
        if self._selected_index is not None and 0 <= self._selected_index < self.model.count():
            return [self._selected_index]
        return []

    def _get_active_index(self) -> int | None:
        """Returns the currently selected index, falling back to cached _selected_index."""
        indices = self.get_selected_indices()
        return indices[0] if indices else None

    def _handle_rename(self) -> None:
        indices = self.get_selected_indices()
        if len(indices) != 1:
            return
        idx = indices[0]

        shot = self.model.shots[idx]
        current_name = shot.custom_name or shot.page_title or f"screenshot_{idx + 1}"

        def validate_name(name: str) -> tuple[bool, str]:
            if not name.strip():
                return False, t("error_empty_name")
            if self.model.is_name_duplicate(name, exclude_index=idx):
                return False, t("error_duplicate_name")
            return True, ""

        dialog = RenameDialog(
            parent=self.winfo_toplevel(),
            current_name=current_name,
            validator=validate_name,
        )
        self.winfo_toplevel().wait_window(dialog)

        if dialog.result is not None:
            if self.model.rename(idx, dialog.result):
                self.refresh_list(select_index=idx)

    def _handle_move_up(self) -> None:
        indices = self.get_selected_indices()
        if len(indices) != 1:
            return
        idx = indices[0]
        if self.model.move_up(idx):
            self.refresh_list(select_index=idx - 1)
        else:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self.listbox.activate(idx)
            self._handle_select(idx)

    def _handle_move_down(self) -> None:
        indices = self.get_selected_indices()
        if len(indices) != 1:
            return
        idx = indices[0]
        if self.model.move_down(idx):
            self.refresh_list(select_index=idx + 1)
        else:
            self.listbox.selection_clear(0, tk.END)
            self.listbox.selection_set(idx)
            self.listbox.activate(idx)
            self._handle_select(idx)

    def _handle_delete(self) -> None:
        indices = self.get_selected_indices()
        if not indices:
            return

        count = len(indices)
        display_name = ""
        if count == 1:
            shot = self.model.shots[indices[0]]
            display_name = shot.custom_name or shot.page_title or f"screenshot_{indices[0] + 1}"
            if len(display_name) > 35:
                display_name = display_name[:32] + "..."

        dialog = ConfirmDeleteDialog(
            parent=self.winfo_toplevel(),
            item_name=display_name,
            count=count,
        )
        self.winfo_toplevel().wait_window(dialog)

        if not dialog.result:
            return

        first_idx = indices[0]
        self.model.delete_multiple(indices)

        # Select previous or next item cleanly without boundary anomalies
        remaining = self.model.count()
        if remaining > 0:
            new_sel = max(0, min(first_idx, remaining - 1))
        else:
            new_sel = None
        self.refresh_list(select_index=new_sel)

    def _handle_reorder(self, from_idx: int, to_idx: int) -> None:
        self.model.reorder(from_idx, to_idx)
        self._selected_index = to_idx
        self._handle_select(to_idx)
        if self.on_list_changed:
            self.on_list_changed()

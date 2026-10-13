"""Top toolbar component for SnapFlow."""

from __future__ import annotations

from typing import Callable
import webbrowser
import customtkinter as ctk
from config_manager import ConfigManager
from i18n import get_current_locale, t

LANG_OPTIONS: dict[str, str] = {
    "English": "en_us",
    "繁體中文": "zh_tw",
    "Bahasa Melayu": "ms_my",
}
LOCALE_TO_LANG: dict[str, str] = {v: k for k, v in LANG_OPTIONS.items()}


class Toolbar(ctk.CTkFrame):
    """Application toolbar providing browser launch, tab management, capture controls, language and theme switcher."""

    def __init__(
        self,
        master: ctk.CTk,
        config_mgr: ConfigManager,
        on_launch: Callable[[], None],
        on_new_tab: Callable[[], None],
        on_viewport: Callable[[], None],
        on_fullpage: Callable[[], None],
        on_range_start: Callable[[], None] | None = None,
        on_range_confirm: Callable[[], None] | None = None,
        on_range_cancel: Callable[[], None] | None = None,
        on_theme_changed: Callable[[str], None] | None = None,
        on_language_changed: Callable[[str], None] | None = None,
        on_delay_changed: Callable[[int], None] | None = None,
        on_tab_selected: Callable[[int], None] | None = None,
    ) -> None:
        super().__init__(master, corner_radius=0)
        self.config_mgr = config_mgr
        self.on_launch = on_launch
        self.on_new_tab = on_new_tab
        self.on_viewport = on_viewport
        self.on_fullpage = on_fullpage
        self.on_range_start = on_range_start
        self.on_range_confirm = on_range_confirm
        self.on_range_cancel = on_range_cancel
        self.on_theme_changed = on_theme_changed or (lambda m: None)
        self.on_language_changed = on_language_changed or (lambda l: None)
        self.on_delay_changed = on_delay_changed or (lambda d: None)
        self.on_tab_selected = on_tab_selected

        self.browser_is_running: bool = False
        self._current_page_title: str = ""
        self._current_page_url: str = ""
        self._browser_was_closed: bool = False
        self._tabs_data: list[dict] = []
        self._is_updating_tab_menu: bool = False
        self._is_in_range_mode: bool = False
        self._range_start_y: int = 0

        self._build_ui()

    def _build_ui(self) -> None:
        # Top Flex Container: Two Columns (Left Column & Right Column)
        flex_container = ctk.CTkFrame(self, fg_color="transparent")
        flex_container.pack(fill="x", padx=16, pady=(8, 4))

        left_col = ctk.CTkFrame(flex_container, fg_color="transparent")
        left_col.pack(side="left", fill="both", expand=True)

        right_col = ctk.CTkFrame(flex_container, fg_color="transparent")
        right_col.pack(side="right", fill="y", padx=(16, 0))

        # ----------------- Left Column (上下排) -----------------
        # L1: Launch Browser & New Tab
        l_row1 = ctk.CTkFrame(left_col, fg_color="transparent")
        l_row1.pack(fill="x", pady=(0, 6))

        self.btn_launch = ctk.CTkButton(
            l_row1,
            text=t("btn_launch_browser"),
            font=ctk.CTkFont(size=13, weight="bold"),
            command=self.on_launch,
            height=32,
            width=140,
        )
        self.btn_launch.pack(side="left", padx=(0, 8))

        self.btn_new_tab = ctk.CTkButton(
            l_row1,
            text=f"➕ {t('btn_new_tab')}",
            command=self.on_new_tab,
            state="disabled",
            height=32,
            fg_color="#0288D1",
            hover_color="#0277BD",
            width=110,
        )
        self.btn_new_tab.pack(side="left")

        # L2: Tabs dropdown and active page info
        l_row2 = ctk.CTkFrame(left_col, fg_color="transparent")
        l_row2.pack(fill="x", pady=(0, 6))

        self.tab_selector_frame = ctk.CTkFrame(l_row2, fg_color="transparent")
        self.tab_selector_frame.pack(side="left", padx=(0, 10))

        self.lbl_tab_prompt = ctk.CTkLabel(
            self.tab_selector_frame,
            text=t("label_tab"),
            font=ctk.CTkFont(size=12, weight="bold"),
        )
        self.lbl_tab_prompt.pack(side="left", padx=(0, 4))

        self.tab_var = ctk.StringVar(value="--")
        self.tab_menu = ctk.CTkOptionMenu(
            self.tab_selector_frame,
            values=["--"],
            variable=self.tab_var,
            command=self._handle_tab_selected,
            width=280,
            height=28,
            state="disabled",
        )
        self.tab_menu.pack(side="left")

        self.lbl_page_status = ctk.CTkLabel(
            l_row2,
            text=f"🌐 {t('label_no_browser')}",
            font=ctk.CTkFont(size=12),
            text_color=("gray40", "gray70"),
            anchor="w",
        )
        self.lbl_page_status.pack(side="left", fill="x", expand=True)

        # L3: Delay slider
        l_row3 = ctk.CTkFrame(left_col, fg_color="transparent")
        l_row3.pack(fill="x", pady=(0, 6))

        self.lbl_delay = ctk.CTkLabel(
            l_row3,
            text=t("label_delay"),
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.lbl_delay.pack(side="left", padx=(0, 4))

        initial_delay = self.config_mgr.capture_delay
        self.slider_delay = ctk.CTkSlider(
            l_row3,
            from_=1,
            to=5,
            number_of_steps=4,
            width=110,
            command=self._handle_delay_slider_change,
        )
        self.slider_delay.set(initial_delay)
        self.slider_delay.pack(side="left", padx=(0, 4))

        self.lbl_delay_val = ctk.CTkLabel(
            l_row3,
            text=f"{initial_delay}s",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=24,
            anchor="w",
        )
        self.lbl_delay_val.pack(side="left")

        # L4: 3 Capture buttons (Viewport, Full Page, Range)
        l_row4 = ctk.CTkFrame(left_col, fg_color="transparent")
        l_row4.pack(fill="x", pady=(0, 2))

        # Viewport screenshot button
        self.btn_viewport = ctk.CTkButton(
            l_row4,
            text=t("btn_screenshot_viewport"),
            command=self.on_viewport,
            state="disabled",
            height=30,
        )
        self.btn_viewport.pack(side="left", padx=(0, 6))

        # Full page screenshot button
        self.btn_fullpage = ctk.CTkButton(
            l_row4,
            text=t("btn_screenshot_fullpage"),
            command=self.on_fullpage,
            state="disabled",
            height=30,
        )
        self.btn_fullpage.pack(side="left", padx=(0, 6))

        # Range screenshot button
        self.btn_range = ctk.CTkButton(
            l_row4,
            text=t("btn_screenshot_range"),
            command=self._handle_range_button_click,
            state="disabled",
            height=30,
            fg_color="#6A1B9A",
            hover_color="#4A148C",
        )
        self.btn_range.pack(side="left")

        # ----------------- Right Column (上下排) -----------------
        # R1: Language Selector
        lang_row = ctk.CTkFrame(right_col, fg_color="transparent")
        lang_row.pack(fill="x", pady=(0, 3))

        self.lang_lbl = ctk.CTkLabel(
            lang_row,
            text=t("label_language"),
            font=ctk.CTkFont(size=11),
            width=55,
            anchor="e",
        )
        self.lang_lbl.pack(side="left", padx=(0, 4))

        cur_locale = get_current_locale()
        initial_lang_name = LOCALE_TO_LANG.get(cur_locale, "English")
        self.lang_var = ctk.StringVar(value=initial_lang_name)
        self.lang_menu = ctk.CTkOptionMenu(
            lang_row,
            values=list(LANG_OPTIONS.keys()),
            variable=self.lang_var,
            command=self._handle_language_change,
            width=120,
            height=26,
            font=ctk.CTkFont(size=11),
        )
        self.lang_menu.pack(side="left")

        # R2: Theme Selector
        theme_row = ctk.CTkFrame(right_col, fg_color="transparent")
        theme_row.pack(fill="x", pady=(0, 3))

        self.theme_lbl = ctk.CTkLabel(
            theme_row,
            text=t("label_theme"),
            font=ctk.CTkFont(size=11),
            width=55,
            anchor="e",
        )
        self.theme_lbl.pack(side="left", padx=(0, 4))

        theme_values = [t("theme_light"), t("theme_dark"), t("theme_auto")]
        initial_theme_val = self._config_to_display_theme(self.config_mgr.theme)
        self.theme_var = ctk.StringVar(value=initial_theme_val)
        self.theme_menu = ctk.CTkOptionMenu(
            theme_row,
            values=theme_values,
            variable=self.theme_var,
            command=self._handle_theme_change,
            width=120,
            height=26,
            font=ctk.CTkFont(size=11),
        )
        self.theme_menu.pack(side="left")

        # R3: Buy Me a Coffee Button
        donate_row = ctk.CTkFrame(right_col, fg_color="transparent")
        donate_row.pack(fill="x", pady=(3, 2))

        self.btn_donate = ctk.CTkButton(
            donate_row,
            text=t("btn_donate"),
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#FF813F",
            hover_color="#E66A28",
            text_color="#FFFFFF",
            corner_radius=6,
            height=26,
            command=self._open_donation_link,
        )
        self.btn_donate.pack(fill="x")

        # R4: GitHub Link Button
        github_row = ctk.CTkFrame(right_col, fg_color="transparent")
        github_row.pack(fill="x", pady=(2, 2))

        self.btn_github = ctk.CTkButton(
            github_row,
            text="GitHub",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#24292E", "#24292E"),
            hover_color=("#1B1F23", "#1B1F23"),
            text_color="#FFFFFF",
            corner_radius=6,
            height=26,
            command=self._open_github_link,
        )
        self.btn_github.pack(fill="x")

        # R5: Version & Developer info
        info_row = ctk.CTkFrame(right_col, fg_color="transparent")
        info_row.pack(fill="x", pady=(0, 0))

        self.lbl_version = ctk.CTkLabel(
            info_row,
            text="Version: 1.0",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("gray30", "gray75"),
            anchor="center",
            height=16,
        )
        self.lbl_version.pack(fill="x", pady=(1, 0))

        self.lbl_author = ctk.CTkLabel(
            info_row,
            text="Developer: cylee",
            font=ctk.CTkFont(size=11),
            text_color=("gray40", "gray70"),
            anchor="center",
            height=16,
        )
        self.lbl_author.pack(fill="x", pady=(0, 0))

        # Range capture interactive banner (hidden by default)
        self.range_banner = ctk.CTkFrame(self, fg_color=("#EDE7F6", "#311B92"), corner_radius=8)
        self.lbl_range_banner = ctk.CTkLabel(
            self.range_banner,
            text="",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color=("#4A148C", "#E1BEE7"),
            anchor="w",
        )
        self.lbl_range_banner.pack(side="left", padx=12, pady=6, fill="x", expand=True)

        self.btn_range_confirm = ctk.CTkButton(
            self.range_banner,
            text=t("banner_range_btn_confirm"),
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2E7D32",
            hover_color="#1B5E20",
            width=110,
            height=28,
            command=self._handle_range_confirm_click,
        )
        self.btn_range_confirm.pack(side="right", padx=(4, 10), pady=6)

        self.btn_range_cancel = ctk.CTkButton(
            self.range_banner,
            text=t("banner_range_btn_cancel"),
            font=ctk.CTkFont(size=12),
            fg_color=("gray70", "gray40"),
            hover_color=("gray60", "gray30"),
            text_color=("black", "white"),
            width=70,
            height=28,
            command=self._handle_range_cancel_click,
        )
        self.btn_range_cancel.pack(side="right", padx=(4, 4), pady=6)

    def _handle_range_button_click(self) -> None:
        if self.on_range_start:
            self.on_range_start()

    def _handle_range_confirm_click(self) -> None:
        self.set_range_mode(False)
        if self.on_range_confirm:
            self.on_range_confirm()

    def _handle_range_cancel_click(self) -> None:
        self.set_range_mode(False)
        if self.on_range_cancel:
            self.on_range_cancel()

    def set_range_mode(self, active: bool, start_y: int = 0) -> None:
        """Shows/hides the range confirmation banner and adjusts button states."""
        self._is_in_range_mode = active
        self._range_start_y = start_y
        if active:
            self.lbl_range_banner.configure(
                text=t("banner_range_start", top=start_y)
            )
            self.range_banner.pack(fill="x", padx=16, pady=(0, 8))
            self.btn_range.configure(state="disabled")
            self.btn_viewport.configure(state="disabled")
            self.btn_fullpage.configure(state="disabled")
        else:
            self.range_banner.pack_forget()
            if self.browser_is_running:
                self.btn_range.configure(state="normal")
                self.btn_viewport.configure(state="normal")
                self.btn_fullpage.configure(state="normal")

    def set_browser_running(self, running: bool, was_closed: bool = False) -> None:
        """Updates toolbar button states depending on whether browser is running."""
        self.browser_is_running = running
        self._browser_was_closed = was_closed

        if not running:
            self.set_range_mode(False)

        if running:
            self._browser_was_closed = False
            self.btn_launch.configure(
                text=f"✓ {t('btn_browser_running')}",
                state="disabled",
                fg_color=("gray65", "gray40"),
            )
            self.btn_new_tab.configure(state="normal")
            self.btn_viewport.configure(state="normal")
            self.btn_fullpage.configure(state="normal")
            self.btn_range.configure(state="normal")
        else:
            self.btn_launch.configure(
                text=t("btn_launch_browser"),
                state="normal",
                fg_color=("#3B8ED0", "#1F6AA5"),
            )
            self.btn_new_tab.configure(state="disabled")
            self.btn_viewport.configure(state="disabled")
            self.btn_fullpage.configure(state="disabled")
            self.btn_range.configure(state="disabled")
            self.tab_menu.configure(state="disabled", values=["--"])
            self.tab_var.set("--")
            self._tabs_data = []
            if was_closed:
                self.lbl_page_status.configure(
                    text=f"⚠️ {t('label_browser_closed')}",
                    text_color=("#D97706", "#FBBF24"),
                )
            else:
                self.lbl_page_status.configure(
                    text=f"🌐 {t('label_no_browser')}",
                    text_color=("gray40", "gray70"),
                )

    def update_tabs_list(self, tabs: list[dict], active_index: int) -> None:
        """Populates the tab Dropdown List with current open tabs."""
        self._tabs_data = tabs
        if not tabs:
            self.tab_menu.configure(state="disabled", values=["--"])
            self.tab_var.set("--")
            return

        display_options = []
        for item in tabs:
            idx = item["index"] + 1
            title = item["title"] or "Untitled"
            if len(title) > 28:
                title = title[:25] + "..."
            display_options.append(f"{idx}. {title}")

        self._is_updating_tab_menu = True
        try:
            self.tab_menu.configure(state="normal", values=display_options)
            if 0 <= active_index < len(display_options):
                self.tab_var.set(display_options[active_index])
            else:
                self.tab_var.set(display_options[0])
        finally:
            self._is_updating_tab_menu = False

    def _handle_tab_selected(self, selected_text: str) -> None:
        """Triggered when user selects a tab from the Dropdown List."""
        if self._is_updating_tab_menu:
            return
        if not self._tabs_data or not selected_text:
            return

        # Find which tab index matches
        for item in self._tabs_data:
            idx_str = f"{item['index'] + 1}."
            if selected_text.startswith(idx_str):
                if self.on_tab_selected:
                    self.on_tab_selected(item["index"])
                break

    def set_active_page_info(self, title: str, url: str) -> None:
        """Updates active page title label."""
        self._current_page_title = title
        self._current_page_url = url

        if not self.browser_is_running:
            if self._browser_was_closed:
                self.lbl_page_status.configure(
                    text=f"⚠️ {t('label_browser_closed')}",
                    text_color=("#D97706", "#FBBF24"),
                )
            else:
                self.lbl_page_status.configure(
                    text=f"🌐 {t('label_no_browser')}",
                    text_color=("gray40", "gray70"),
                )
            return

        if not title and not url:
            self.lbl_page_status.configure(
                text=f"🌐 {t('label_no_browser')}",
                text_color=("gray40", "gray70"),
            )
            return

        display_text = title if title else url
        if len(display_text) > 85:
            display_text = display_text[:82] + "..."

        self.lbl_page_status.configure(
            text=f"🌐 {t('label_active_page', title=display_text)}",
            text_color=("gray10", "gray90"),
        )

    def refresh_ui_texts(self) -> None:
        """Dynamically refreshes all label and button texts according to active locale."""
        if self.browser_is_running:
            self.btn_launch.configure(text=f"✓ {t('btn_browser_running')}")
        else:
            self.btn_launch.configure(text=t("btn_launch_browser"))

        self.btn_new_tab.configure(text=f"➕ {t('btn_new_tab')}")
        self.btn_viewport.configure(text=t("btn_screenshot_viewport"))
        self.btn_fullpage.configure(text=t("btn_screenshot_fullpage"))
        self.btn_range.configure(text=t("btn_screenshot_range"))
        self.btn_range_confirm.configure(text=t("banner_range_btn_confirm"))
        self.btn_range_cancel.configure(text=t("banner_range_btn_cancel"))
        if self._is_in_range_mode:
            self.lbl_range_banner.configure(text=t("banner_range_start", top=self._range_start_y))

        self.lbl_tab_prompt.configure(text=t("label_tab"))
        self.lbl_delay.configure(text=t("label_delay"))
        self.lang_lbl.configure(text=t("label_language"))
        self.theme_lbl.configure(text=t("label_theme"))
        self.btn_donate.configure(text=t("btn_donate"))
        cur_locale = get_current_locale()
        self.lang_var.set(LOCALE_TO_LANG.get(cur_locale, "English"))

        theme_values = [t("theme_light"), t("theme_dark"), t("theme_auto")]
        self.theme_menu.configure(values=theme_values)
        self.theme_var.set(self._config_to_display_theme(self.config_mgr.theme))

        self.set_active_page_info(self._current_page_title, self._current_page_url)

    def _handle_delay_slider_change(self, value: float) -> None:
        """Triggered when user adjusts the capture delay slider (1s to 5s)."""
        int_val = int(round(value))
        self.lbl_delay_val.configure(text=f"{int_val}s")
        if self.on_delay_changed:
            self.on_delay_changed(int_val)

    def _config_to_display_theme(self, mode: str) -> str:
        if mode == "dark":
            return t("theme_dark")
        elif mode == "system":
            return t("theme_auto")
        return t("theme_light")

    def _display_to_config_theme(self, display_text: str) -> str:
        if display_text == t("theme_dark"):
            return "dark"
        elif display_text == t("theme_auto"):
            return "system"
        return "light"

    def _handle_theme_change(self, value: str) -> None:
        raw_mode = self._display_to_config_theme(value)
        self.on_theme_changed(raw_mode)

    def _handle_language_change(self, display_name: str) -> None:
        locale_code = LANG_OPTIONS.get(display_name, "en_us")
        self.on_language_changed(locale_code)

    def _open_donation_link(self) -> None:
        """Opens user's Buy Me a Coffee page in system's default web browser."""
        webbrowser.open_new_tab("https://buymeacoffee.com/cylee99")

    def _open_github_link(self) -> None:
        """Opens project GitHub repository in system's default web browser."""
        webbrowser.open_new_tab("https://github.com/leechunyen/SnapFlow.git")

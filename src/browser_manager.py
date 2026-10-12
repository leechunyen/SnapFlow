"""Playwright browser lifecycle and screenshot management.

Runs Playwright's sync API in a dedicated background worker thread to ensure
that Tkinter's main event loop remains fully responsive. Tracks the active
tab dynamically and handles full page and viewport screenshots.
"""

from __future__ import annotations

import queue
import threading
import time
from typing import Any, Callable
from playwright.sync_api import Browser, BrowserContext, Page, sync_playwright


class BrowserManager:
    """Manages Chromium browser instance and capture commands in a background thread."""

    def __init__(
        self,
        capture_delay: int = 1,
        on_browser_started: Callable[[], None] | None = None,
        on_browser_closed: Callable[[], None] | None = None,
        on_page_title_changed: Callable[[str, str], None] | None = None,
        on_tabs_updated: Callable[[list[dict], int], None] | None = None,
        on_screenshot_captured: Callable[[bytes, str, str, bool], None] | None = None,
        on_range_start_ready: Callable[[int], None] | None = None,
        on_error: Callable[[str], None] | None = None,
    ) -> None:
        self.capture_delay: float = float(max(1, min(5, capture_delay)))
        self.on_browser_started = on_browser_started
        self.on_browser_closed = on_browser_closed
        self.on_page_title_changed = on_page_title_changed
        self.on_tabs_updated = on_tabs_updated
        self.on_screenshot_captured = on_screenshot_captured
        self.on_range_start_ready = on_range_start_ready
        self.on_error = on_error

        self._thread: threading.Thread | None = None
        self._cmd_queue: queue.Queue = queue.Queue()
        self._stop_event = threading.Event()

        self._active_page: Page | None = None
        self._last_title: str = ""
        self._last_url: str = ""
        self._last_tabs_signature: str = ""
        self.is_running: bool = False
        self._range_start_y: int | None = None

    def _safe_invoke_callback(self, callback: Callable | None, *args: Any) -> None:
        """Safely invokes a UI/consumer callback, preventing unhandled exceptions in background threads."""
        if callback:
            try:
                callback(*args)
            except Exception as e:
                print(f"[BrowserManager] Exception in callback {callback}: {e}")

    def launch(self) -> None:
        """Launches the Chromium browser in a background thread if not already running."""
        if self.is_running:
            return

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        # Clear leftover commands from previous runs
        while not self._cmd_queue.empty():
            try:
                self._cmd_queue.get_nowait()
            except queue.Empty:
                break

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._worker_loop, daemon=True)
        self._thread.start()

    def request_screenshot(self, full_page: bool = False) -> None:
        """Enqueues a screenshot request for the active tab."""
        if self.is_running:
            self._cmd_queue.put(("SCREENSHOT", full_page))

    def request_start_range_capture(self) -> None:
        """Enqueues a request to record the current scroll position as range start."""
        if self.is_running:
            self._cmd_queue.put(("START_RANGE", None))

    def request_confirm_range_capture(self) -> None:
        """Enqueues a request to capture screenshot from start_y down to current scroll position."""
        if self.is_running:
            self._cmd_queue.put(("CONFIRM_RANGE", None))

    def cancel_range_capture(self) -> None:
        """Cancels current pending range capture."""
        self._range_start_y = None

    def request_new_tab(self, url: str = "https://www.google.com") -> None:
        """Enqueues a request to open a new tab."""
        if self.is_running:
            self._cmd_queue.put(("NEW_TAB", url))

    def switch_tab(self, tab_index: int) -> None:
        """Enqueues a request to explicitly switch active tab to tab_index."""
        if self.is_running:
            self._cmd_queue.put(("SWITCH_TAB", tab_index))

    def close(self, wait: bool = True) -> None:
        """Requests graceful shutdown of the browser and worker thread."""
        if self.is_running:
            self._stop_event.set()
            self._cmd_queue.put(("STOP", None))
            if wait and self._thread and self._thread.is_alive():
                # Allow Playwright driver subprocess and pages to cleanly close pipes
                self._thread.join(timeout=3.5)

    def _worker_loop(self) -> None:
        """Worker thread entry point."""
        playwright_context = None
        browser: Browser | None = None
        context: BrowserContext | None = None

        try:
            playwright_context = sync_playwright().start()
            launch_args = [
                "--start-maximized",
                "--no-default-browser-check",
                "--no-first-run",
                "--disable-blink-features=AutomationControlled",
                "--disable-breakpad",
                "--disable-component-update",
            ]
            ignore_args = ["--enable-automation"]

            # Helper to search for Brave binary across standard install locations
            def _find_brave_binary() -> str | None:
                import os
                import sys
                from pathlib import Path
                candidates = []
                if sys.platform.startswith("win"):
                    for env_var in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
                        base = os.environ.get(env_var)
                        if base:
                            candidates.append(Path(base) / "BraveSoftware" / "Brave-Browser" / "Application" / "brave.exe")
                elif sys.platform == "darwin":
                    candidates.append(Path("/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"))
                elif sys.platform.startswith("linux"):
                    candidates.append(Path("/usr/bin/brave-browser"))
                    candidates.append(Path("/usr/bin/brave"))
                for p in candidates:
                    if p.exists():
                        return str(p)
                return None

            # Browser Fallback Chain: Chrome -> Microsoft Edge -> Brave -> Playwright Chromium
            launch_attempts = [
                ("chrome", {"channel": "chrome"}),
                ("msedge", {"channel": "msedge"}),
            ]
            brave_path = _find_brave_binary()
            if brave_path:
                launch_attempts.append(("brave", {"executable_path": brave_path}))
            launch_attempts.append(("chromium", {}))  # Bundled Playwright chromium

            for b_name, b_kwargs in launch_attempts:
                try:
                    browser = playwright_context.chromium.launch(
                        **b_kwargs,
                        headless=False,
                        args=launch_args,
                        ignore_default_args=ignore_args,
                    )
                    print(f"[SnapFlow] Successfully launched browser using: {b_name}")
                    break
                except Exception as e:
                    continue

            if not browser:
                import i18n
                raise RuntimeError(i18n.t("error_browser_not_installed"))

            # Create a context with no fixed viewport and standard user agent
            context = browser.new_context(
                no_viewport=True,
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
            )
            # Conceal navigator.webdriver automation signature
            context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")

            def on_page_created(new_page: Page) -> None:
                """Track newly opened tab as active."""
                self._active_page = new_page
                self._poll_page_info()

            context.on("page", on_page_created)

            self.is_running = True
            self._safe_invoke_callback(self.on_browser_started)

            self._active_page = context.new_page()
            try:
                self._active_page.goto("https://www.google.com", timeout=15000, wait_until="domcontentloaded")
            except Exception as nav_err:
                print(f"[BrowserManager] Initial navigation notice: {nav_err}")

            self._poll_page_info()

            last_poll_time = 0.0

            while not self._stop_event.is_set():
                # Process commands from queue
                try:
                    cmd, arg = self._cmd_queue.get(timeout=0.2)
                    if cmd == "STOP":
                        break
                    elif cmd == "SCREENSHOT":
                        self._handle_screenshot(context, full_page=bool(arg))
                    elif cmd == "START_RANGE":
                        self._handle_start_range(context)
                    elif cmd == "CONFIRM_RANGE":
                        self._handle_confirm_range(context)
                    elif cmd == "NEW_TAB":
                        self._handle_new_tab(context, url=str(arg) if arg else "https://www.google.com")
                    elif cmd == "SWITCH_TAB":
                        self._handle_switch_tab(context, int(arg))
                except queue.Empty:
                    pass

                # Check if browser is still alive
                if not browser or not browser.is_connected():
                    break

                # Periodic page status poll every 0.6s
                now = time.time()
                if now - last_poll_time > 0.6:
                    last_poll_time = now
                    self._check_and_poll_active_page(context)

        except Exception as e:
            if not self._stop_event.is_set():
                err_msg = str(e)
                print(f"[BrowserManager] Worker error: {err_msg}")
                self._safe_invoke_callback(self.on_error, err_msg)
        finally:
            self.is_running = False
            self._active_page = None

            # 1. Close individual pages first to allow renderer processes to exit cleanly
            if context:
                try:
                    for p in list(context.pages):
                        try:
                            if not p.is_closed():
                                p.close()
                        except Exception:
                            pass
                except Exception:
                    pass

            # 2. Close browser context
            if context:
                try:
                    context.close()
                except Exception:
                    pass

            # 3. Close browser gracefully
            if browser:
                try:
                    if browser.is_connected():
                        browser.close()
                except Exception:
                    pass

            # 4. Stop playwright node driver
            if playwright_context:
                try:
                    playwright_context.stop()
                except Exception:
                    pass

            self._safe_invoke_callback(self.on_browser_closed)

    def _handle_switch_tab(self, context: BrowserContext | None, tab_index: int) -> None:
        """Explicitly sets the active tab from user selection in Dropdown List without stealing focus."""
        if not context:
            return
        pages = [p for p in context.pages if not p.is_closed()]
        if 0 <= tab_index < len(pages):
            self._active_page = pages[tab_index]
            self._poll_page_info()
            self._notify_tabs_list(context)

    def _get_valid_active_page(self, context: BrowserContext | None) -> Page | None:
        """Returns the current active page or falls back to the latest valid page."""
        if context:
            pages = [p for p in context.pages if not p.is_closed()]
            if not pages:
                self._active_page = None
                return None

            if self._active_page and not self._active_page.is_closed() and self._active_page in pages:
                return self._active_page

            self._active_page = pages[-1]
            return self._active_page

        self._active_page = None
        return None

    def _check_and_poll_active_page(self, context: BrowserContext | None) -> None:
        """Polls current active page's title and URL to update GUI label and tab list."""
        page = self._get_valid_active_page(context)
        if not page:
            if self._last_title != "":
                self._last_title = ""
                self._last_url = ""
                if self.on_page_title_changed:
                    self.on_page_title_changed("", "")
                if self.on_tabs_updated:
                    self.on_tabs_updated([], -1)
            return

        try:
            title = page.title() or ""
            url = page.url or ""
            if title != self._last_title or url != self._last_url:
                self._last_title = title
                self._last_url = url
                if self.on_page_title_changed:
                    self.on_page_title_changed(title, url)
        except Exception:
            pass

        self._notify_tabs_list(context)

    def _notify_tabs_list(self, context: BrowserContext | None) -> None:
        """Emits updated list of open tabs to UI for Dropdown selection."""
        if not context or not self.on_tabs_updated:
            return

        try:
            pages = [p for p in context.pages if not p.is_closed()]
            tabs_info = []
            active_idx = 0
            for i, p in enumerate(pages):
                if p == self._active_page:
                    active_idx = i
                t = p.title() or "Untitled"
                u = p.url or ""
                tabs_info.append({"index": i, "title": t, "url": u})

            # Check if signature changed to avoid unnecessary GUI updates
            signature = "|".join(f"{item['index']}:{item['title']}:{item['url']}" for item in tabs_info)
            signature += f"||active:{active_idx}"

            if signature != self._last_tabs_signature:
                self._last_tabs_signature = signature
                self.on_tabs_updated(tabs_info, active_idx)
        except Exception:
            pass

    def _poll_page_info(self) -> None:
        """Forces title/url update check immediately."""
        if self._active_page and not self._active_page.is_closed():
            try:
                t = self._active_page.title() or ""
                u = self._active_page.url or ""
                self._last_title, self._last_url = t, u
                if self.on_page_title_changed:
                    self.on_page_title_changed(t, u)
            except Exception:
                pass

    def _handle_new_tab(self, context: BrowserContext | None, url: str) -> None:
        """Opens a new tab in the running browser context."""
        if not context:
            return
        try:
            new_page = context.new_page()
            try:
                new_page.goto(url, timeout=15000, wait_until="domcontentloaded")
            except Exception:
                pass
            self._active_page = new_page
            self._poll_page_info()
        except Exception as e:
            print(f"[BrowserManager] Failed to create new tab: {e}")

    def _prepare_page_for_capture(self, page: Page, trigger_lazy_load: bool = False) -> None:
        """Stabilizes web animations and triggers lazy-loaded content before capturing.
        
        - Injects CSS to freeze transitions, CSS keyframe animations, and force full opacity
          on scroll-triggered elements (like AOS, WOW.js, GSAP).
        - Optionally pre-scrolls through the page to trigger IntersectionObserver lazy images.
        """
        try:
            # 1. Inject anti-animation and full opacity stylesheet
            page.evaluate("""() => {
                let style = document.getElementById('__snapflow_animation_freeze__');
                if (!style) {
                    style = document.createElement('style');
                    style.id = '__snapflow_animation_freeze__';
                    style.textContent = `
                        *, *::before, *::after {
                            transition-duration: 0s !important;
                            transition-delay: 0s !important;
                            animation-duration: 0s !important;
                            animation-delay: 0s !important;
                        }
                        /* Ensure scroll-revealed elements (AOS / GSAP / WOW) are fully visible */
                        [data-aos], .wow, [class*="animate-"], [class*="fade-"] {
                            opacity: 1 !important;
                            visibility: visible !important;
                            transform: none !important;
                        }
                    `;
                    document.head.appendChild(style);
                }
            }""")
        except Exception:
            pass

        if trigger_lazy_load:
            try:
                # 2. Trigger lazy images via incremental scroll and give JS observers time to process
                page.evaluate("""async () => {
                    const scrollHeight = Math.max(
                        document.body ? document.body.scrollHeight : 0,
                        document.documentElement ? document.documentElement.scrollHeight : 0
                    );
                    const step = window.innerHeight || 800;
                    for (let y = 0; y < Math.min(scrollHeight, 15000); y += step) {
                        window.scrollTo(0, y);
                        await new Promise(r => setTimeout(r, 60));
                    }
                    // CRITICAL: Always scroll back to the very top so the page is at (0, 0)
                    window.scrollTo(0, 0);
                }""")
                # Let lazy network image requests settle
                try:
                    page.wait_for_load_state("networkidle", timeout=1200)
                except Exception:
                    time.sleep(0.3)
                # Extra ensure scroll at top
                page.evaluate("() => window.scrollTo(0, 0)")
            except Exception:
                pass
        else:
            # Viewport capture: wait for pending rAF/JS frame callbacks to finish
            try:
                page.evaluate("() => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))")
            except Exception:
                pass

        # Apply user-configured capture delay (1s to 5s) for JS rendering/animations to settle
        delay_time = max(0.5, self.capture_delay)
        time.sleep(delay_time)

    def _cleanup_page_after_capture(self, page: Page) -> None:
        """Removes injected animation-freeze stylesheet to restore natural browser browsing."""
        try:
            page.evaluate("""() => {
                const style = document.getElementById('__snapflow_animation_freeze__');
                if (style) {
                    style.remove();
                }
            }""")
        except Exception:
            pass

    def _handle_screenshot(self, context: BrowserContext | None, full_page: bool) -> None:
        """Executes screenshot on the active tab without bringing window to front."""
        page = self._get_valid_active_page(context)
        if not page:
            if self.on_error:
                self.on_error("No active tab available for capture")
            return

        try:
            actual_full_page = full_page

            try:
                if full_page:
                    try:
                        # 1. Prepare and freeze animations with lazy load triggering
                        self._prepare_page_for_capture(page, trigger_lazy_load=True)
                        # 2. Make sure we are at (0, 0) at the very top of document
                        page.evaluate("() => window.scrollTo(0, 0)")
                        time.sleep(0.3)

                        # 3. For Full Page capture, convert fixed top headers to absolute
                        # Keep its exact top position (e.g. margin/padding from top) rather than forcing top: 0px!
                        page.evaluate("""() => {
                            window.__snapflow_fixed_top_elems = [];
                            const allElems = document.querySelectorAll('*');
                            for (const el of allElems) {
                                try {
                                    const style = window.getComputedStyle(el);
                                    if (style.position === 'fixed') {
                                        const rect = el.getBoundingClientRect();
                                        // If element is docked near top of viewport (e.g. navigation header)
                                        if (rect.top <= 160) {
                                            window.__snapflow_fixed_top_elems.push({
                                                elem: el,
                                                origPosition: el.style.position,
                                                origTop: el.style.top
                                            });
                                            el.style.position = 'absolute';
                                            // Preserve natural top distance (accounting for floating pills / margins)
                                            el.style.top = Math.max(0, rect.top) + 'px';
                                        }
                                    }
                                } catch (e) {}
                            }
                        }""")
                        time.sleep(0.1)

                        img_bytes = page.screenshot(full_page=True, animations="disabled", type="png")
                    except Exception as fp_err:
                        print(f"[BrowserManager] Full page capture error, falling back to viewport: {fp_err}")
                        img_bytes = page.screenshot(full_page=False, animations="disabled", type="png")
                        actual_full_page = False
                        if self.on_error:
                            self.on_error("Webpage is too large for full page capture; fell back to current viewport.")
                    finally:
                        # Restore fixed header positions
                        try:
                            page.evaluate("""() => {
                                if (window.__snapflow_fixed_top_elems) {
                                    for (const item of window.__snapflow_fixed_top_elems) {
                                        try {
                                            item.elem.style.position = item.origPosition;
                                            item.elem.style.top = item.origTop;
                                        } catch (e) {}
                                    }
                                    delete window.__snapflow_fixed_top_elems;
                                }
                            }""")
                        except Exception:
                            pass
                else:
                    self._prepare_page_for_capture(page, trigger_lazy_load=False)
                    img_bytes = page.screenshot(full_page=False, animations="disabled", type="png")
            finally:
                # GUARANTEED CLEANUP: Always remove injected animation-freeze stylesheet
                self._cleanup_page_after_capture(page)

            title = page.title() or "Untitled"
            url = page.url or ""
            if self.on_screenshot_captured:
                self.on_screenshot_captured(img_bytes, title, url, actual_full_page)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Screenshot failed: {e}")

    def _handle_start_range(self, context: BrowserContext | None) -> None:
        """Records current scroll Y position as range start."""
        page = self._get_valid_active_page(context)
        if not page:
            if self.on_error:
                self.on_error("No active tab available for range capture")
            return

        try:
            scroll_pos = page.evaluate("() => Math.round(window.scrollY || window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0)")
            self._range_start_y = max(0, int(scroll_pos))
            if self.on_range_start_ready:
                self.on_range_start_ready(self._range_start_y)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to record start position: {e}")

    def _handle_confirm_range(self, context: BrowserContext | None) -> None:
        """Captures screenshot spanning from the recorded start Y to the current bottom position.

        Uses Playwright native clip screenshot to eliminate duplicate sticky headers and avoid
        seam artifacts.
        """
        page = self._get_valid_active_page(context)
        if not page:
            if self.on_error:
                self.on_error("No active tab available for capture")
            return

        if self._range_start_y is None:
            if self.on_error:
                self.on_error("No start position recorded")
            return

        try:
            # Query current viewport geometry and scroll offsets
            metrics = page.evaluate("""() => {
                const scrollY = Math.round(window.scrollY || window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0);
                const viewportHeight = window.innerHeight;
                const viewportWidth = window.innerWidth;
                const docHeight = Math.max(
                    document.body ? document.body.scrollHeight : 0,
                    document.documentElement ? document.documentElement.scrollHeight : 0,
                    document.body ? document.body.offsetHeight : 0,
                    document.documentElement ? document.documentElement.offsetHeight : 0
                );
                return {
                    scrollY: scrollY,
                    viewportHeight: viewportHeight,
                    viewportWidth: viewportWidth,
                    currentBottom: scrollY + viewportHeight,
                    docHeight: docHeight
                };
            }""")

            start_y = max(0, self._range_start_y)
            viewport_h = int(metrics.get("viewportHeight", 800))
            viewport_w = int(metrics.get("viewportWidth", 1280))
            doc_h = int(metrics.get("docHeight", 2000))
            current_scroll_y = int(metrics.get("scrollY", start_y))
            current_bottom = int(metrics.get("currentBottom", current_scroll_y + viewport_h))

            # Determine range top and bottom
            top_y = min(start_y, current_scroll_y)
            bottom_y = max(start_y + viewport_h, current_bottom)
            total_range_h = max(50, bottom_y - top_y)

            # Clamp height to document boundaries if known
            if doc_h > top_y:
                total_range_h = min(total_range_h, doc_h - top_y)
            import io
            from PIL import Image

            # Slices to stitch: (image, crop_top, crop_h, canvas_offset_y)
            slices: list[tuple[Image.Image, int, int, float]] = []

            # Prepare and freeze animations for range stitching
            self._prepare_page_for_capture(page, trigger_lazy_load=False)
            try:
                # 1. Capture first slice at top_y naturally (preserving the sticky header / search bar at the very top)
                page.evaluate(f"() => window.scrollTo(0, {top_y})")
                time.sleep(0.18)
                actual_top_y = page.evaluate("() => Math.round(window.scrollY || window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0)")
                first_slice_bytes = page.screenshot(full_page=False, animations="disabled", type="png")
                first_slice_img = Image.open(io.BytesIO(first_slice_bytes))

                # How much vertical content we need from this first slice
                take_first_h = max(1, min(viewport_h, bottom_y - actual_top_y))
                slices.append((first_slice_img, 0, take_first_h, 0.0))

                cur_target_y = actual_top_y + take_first_h

                if cur_target_y < bottom_y:
                    # 2. Hide position:fixed / position:sticky (including -webkit-sticky) elements for subsequent slices so they don't repeat
                    page.evaluate("""() => {
                        window.__snapflow_hidden_elems = [];
                        const allElems = document.querySelectorAll('*');
                        for (const el of allElems) {
                            try {
                                const style = window.getComputedStyle(el);
                                const pos = style.position;
                                if (pos === 'fixed' || pos === 'sticky' || pos === '-webkit-sticky') {
                                    window.__snapflow_hidden_elems.push({
                                        elem: el,
                                        origVisibility: el.style.visibility
                                    });
                                    el.style.visibility = 'hidden';
                                }
                            } catch (e) {}
                        }
                    }""")
                    time.sleep(0.08)

                    slice_delay = max(0.18, 0.15 * self.capture_delay)
                    try:
                        while cur_target_y < bottom_y:
                            page.evaluate(f"() => window.scrollTo(0, {cur_target_y})")
                            time.sleep(slice_delay)
                            actual_scroll_y = int(page.evaluate("() => Math.round(window.scrollY || window.pageYOffset || document.documentElement.scrollTop || document.body.scrollTop || 0)"))
                            slice_bytes = page.screenshot(full_page=False, animations="disabled", type="png")
                            slice_img = Image.open(io.BytesIO(slice_bytes))

                            # Where does this slice start relative to cur_target_y?
                            # If actual_scroll_y < cur_target_y (e.g. hit bottom of doc and couldn't scroll down further):
                            # The needed content starts at (cur_target_y - actual_scroll_y) inside this slice
                            slice_offset_in_view = max(0, cur_target_y - actual_scroll_y)
                            needed_h = min(bottom_y - cur_target_y, viewport_h - slice_offset_in_view)
                            if needed_h <= 0:
                                slice_img.close()
                                break

                            canvas_y = float(cur_target_y - top_y)
                            slices.append((slice_img, slice_offset_in_view, needed_h, canvas_y))

                            cur_target_y += needed_h
                    finally:
                        # Restore original element visibility
                        page.evaluate("""() => {
                            if (window.__snapflow_hidden_elems) {
                                for (const item of window.__snapflow_hidden_elems) {
                                    try {
                                        item.elem.style.visibility = item.origVisibility;
                                    } catch (e) {}
                                }
                                delete window.__snapflow_hidden_elems;
                            }
                        }""")
            finally:
                # GUARANTEED CLEANUP: Remove injected freeze styles and restore user scroll
                self._cleanup_page_after_capture(page)
                try:
                    page.evaluate(f"() => window.scrollTo(0, {current_scroll_y})")
                except Exception:
                    pass

            # Stitch all slices together with Pillow using float precision to avoid DPI rounding seam gaps
            scale_factor = slices[0][0].width / viewport_w if viewport_w > 0 else 1.0
            stitched_w = slices[0][0].width
            stitched_h = max(1, round(total_range_h * scale_factor))

            stitched = Image.new("RGB", (stitched_w, stitched_h), (255, 255, 255))
            for s_img, slice_crop_y, take_h, canvas_y in slices:
                scaled_crop_y = round(slice_crop_y * scale_factor)
                scaled_take_h = round(take_h * scale_factor)
                scaled_canvas_y = round(canvas_y * scale_factor)

                crop_box = (0, scaled_crop_y, stitched_w, min(s_img.height, scaled_crop_y + scaled_take_h))
                cropped = s_img.crop(crop_box)
                stitched.paste(cropped, (0, scaled_canvas_y))
                s_img.close()

            buf = io.BytesIO()
            stitched.save(buf, format="PNG")
            img_bytes = buf.getvalue()
            stitched.close()

            title = page.title() or "Untitled"
            url = page.url or ""
            self._range_start_y = None

            if self.on_screenshot_captured:
                self.on_screenshot_captured(img_bytes, title, url, False)
        except Exception as e:
            self._range_start_y = None
            print(f"[BrowserManager] Range capture failed: {e}")
            if self.on_error:
                self.on_error(f"Range capture failed: {e}")

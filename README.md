# SnapFlow 📸

**SnapFlow** is a modern desktop web screenshot and capture management tool built with **Playwright** and **CustomTkinter**. Designed for users who need to interactively browse websites, perform manual authentication/login, and capture clean, precise screenshots (Viewport, Full Page, or Custom Scroll Range) with intuitive previewing, drag-and-drop reordering, renaming, and batch exporting.

---

## ✨ Features

1. **Headful Browser (Chrome / Edge / Brave / Chromium)**:
   - Click "Launch Browser" to browse freely, log into accounts, and interact with web pages.
   - **Multi-Browser Automatic Fallback**: Seamlessly detects and prioritizes installed browsers: **Google Chrome** ➡️ **Microsoft Edge** ➡️ **Brave Browser** ➡️ **Playwright Chromium**. If you have Edge or Brave installed, you don't even need Chrome or Playwright's browser package!
   - Dynamically tracks the **active tab**, page title, and live URL, allowing tab switching directly via the GUI dropdown menu.
   - Safe shutdown lifecycle: shuts down tabs and contexts gracefully to eliminate process crashes (`SIGTRAP`) on macOS.

2. **Three Capture Modes & Adjustable Delay (1s – 5s)**:
   - **📸 Viewport Capture**: Instantly grabs the visible browser screen area.
   - **📑 Full Page Capture**: Faithful full-height capture with smart sticky header handling and infinite-scroll protection.
   - **📍 Scroll Range Capture**: Pinpoint start and end scroll offsets with sub-pixel seamless stitching.
   - **⏱️ Adjustable Capture Delay**: Stabilizes dynamic JS animations and lazy-loaded assets before taking shots. (See [User Guide & Capture Delay](#-user-guide--capture-delay) below for in-depth details).

3. **Loading Modal & Anti-Spam Protection**:
   - Displays an animated loading modal during screenshot captures, range stitching, and application shutdown.
   - Intercepts and blocks user clicks during operations to prevent duplicate requests or UI freezes.
   - Synchronizes toolbar state gracefully even if the external browser is abruptly closed or crashed during capture.

4. **Preview, Multi-Selection & List Management**:
   - **Full-Width Scrollable Preview**: Renders long full-page screenshots at full readable width, enabling smooth vertical scrolling inspection.
   - **Adaptive List Display & Resize Debounce**: Dynamically measures available pixel width and fits screenshot titles cleanly. Debounces resize events to maintain smooth 60fps responsiveness even with dozens of screenshots.
   - **Multi-Selection Preview Clarity**: When multiple items are selected (`Ctrl` / `Cmd`), the single-item preview panel cleanly hides to prevent confusion, while export actions automatically adapt to batch operations.
   - **Custom Renaming & Duplicate Detection**: Rename captures on the fly with instant validation and character sanitization.
   - **Precise Action Controls**:
     - Single item: move up (`▲`), move down (`▼`), or rename (`✏️`).
     - Multi-select: hold `Ctrl` or `Cmd` to select multiple captures for bulk deletion or selective export.
     - Explicit movement via dedicated action buttons (`▲ Up` / `▼ Down`), avoiding accidental jumps from click-dragging.
     - Debounced "Copy URL" with non-overlapping visual feedback timer.

5. **Flexible Export Options**:
   - **Smart Scope Detection**: Dynamically toggles between "Export All" and "Export Selected" depending on current list selection.
   - **Batch PNG Export**: Saves screenshots as individual PNG images with automatic filename conflict handling.
   - **Merged PDF Export**: Flattens and combines screenshots into a single multi-page PDF document on white backgrounds.

6. **Appearance & Themes**:
   - Seamlessly toggle between **Light**, **Dark**, and **System** appearance modes on the fly.
   - User theme preferences are automatically persisted in `~/.snapflow/config.json`.

7. **Internationalization (i18n)**:
   - Full multi-language GUI support for:
     - 🇺🇸 **English** (`en_us`)
     - 🇹🇼 **Traditional Chinese (繁體中文)** (`zh_tw`)
     - 🇲🇾 **Malay (Bahasa Melayu)** (`ms_my`)
   - Automatic system locale detection on launch with dynamic runtime language switching in the toolbar.

8. **Unsaved Changes Safety & Temp Directory Recovery**:
   - Prompts for confirmation when closing the application with unexported screenshots.
   - Automatically cleans up all temporary screenshot files upon exit to save disk space.
   - Detects and cleans up orphaned temporary folders left behind by past system crashes on startup.

---

## 🛠 Installation & Quick Start

Follow these steps to set up your environment and run SnapFlow:

### Step 1: Clone the Repository

```bash
git clone https://github.com/leechunyen/SnapFlow.git
cd SnapFlow
```

---

### Step 2: Set Up Virtual Environment

SnapFlow requires **Python 3.10+**. Follow the instructions below for your operating system:

#### 1. Prerequisites (If `venv` is not already installed)

- **macOS**: Python comes with the built-in `venv` module. (If using Homebrew Python, see the Tkinter note below).
- **Windows**: Standard official Python installers from python.org include `venv` by default.
- **Ubuntu / Debian Linux**: The `venv` package is separated by default. If `python3 -m venv` fails, install it via:
  ```bash
  sudo apt update && sudo apt install python3-venv python3-tk -y
  ```
- **Alternative (via `virtualenv`)**: If you prefer or need `virtualenv`:
  ```bash
  pip install --user virtualenv
  ```

---

#### 2. Create the Virtual Environment

Run one of the following commands in the project root:

- **Using built-in `venv` (Recommended)**:
  ```bash
  # macOS / Linux
  python3 -m venv .venv

  # Windows
  python -m venv .venv
  ```

- **Using `virtualenv`**:
  ```bash
  # macOS / Linux
  virtualenv .venv

  # Windows
  virtualenv .venv
  ```

---

#### 3. Activate the Virtual Environment

- **🍏 macOS / 🐧 Linux (bash / zsh)**:
  ```bash
  source .venv/bin/activate
  ```

- **🪟 Windows (PowerShell)**:
  ```powershell
  .venv\Scripts\Activate.ps1
  ```
  *(If execution is blocked on PowerShell, run `Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned` first)*

- **🪟 Windows (Command Prompt `cmd.exe`)**:
  ```cmd
  .venv\Scripts\activate.bat
  ```

> 💡 **macOS Homebrew Note**:
> If you installed Python via Homebrew (e.g., Python 3.12, 3.13, or 3.14), Homebrew does not package the `tkinter` GUI module by default. If you see `ModuleNotFoundError: No module named '_tkinter'`, install it via:
> ```bash
> brew install python-tk@3.14   # Replace with your installed Python version (e.g., python-tk@3.12)
> ```

---

### Step 3: Install Dependencies

With your virtual environment activated, install all required packages:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

**Core Packages in `requirements.txt`**:
- `customtkinter>=5.2.2`: Modern, customizable GUI widget toolkit
- `playwright>=1.44.0`: Browser automation and screenshot rendering engine
- `Pillow>=10.3.0`: High-resolution slicing, stitching, thumbnailing, and PDF compilation
- `darkdetect>=0.8.0`: Cross-platform OS appearance mode detection

**Optional Packages**:
- `pyobjc-framework-Cocoa>=10.0` (macOS only): Enables native Dock icon badge rendering and system language auto-detection. Can be installed via `pip install pyobjc-framework-Cocoa`.

---

### Step 4: Install Playwright Browser Binaries

If your system already has Google Chrome installed, SnapFlow will prioritize using it automatically. If Chrome is not installed or you prefer using Playwright's dedicated Chromium build, run:

```bash
# Cross-platform reliable invocation:
python -m playwright install chromium
```

*(Using `python -m playwright` avoids `command not found` errors if your Scripts directory is not on system PATH)*

---

## 🚀 Running the Application

Ensure the virtual environment is activated, then launch SnapFlow with `main.py`:

### 1. Default Launch (Auto-detects system language and restores saved theme preference)

```bash
python main.py
```

### 2. Launch with Command-Line Arguments (Optional)

You can override the language or appearance mode on startup via CLI flags:

```bash
# Launch with specific language and theme
python main.py --lang en_us --theme dark
python main.py --lang zh_tw --theme light
python main.py --lang ms_my --theme system
```

**Available CLI Options**:
- `--lang`: `en_us` (English), `zh_tw` (Traditional Chinese), `ms_my` (Malay)
- `--theme`: `light`, `dark`, `system`

---

## 📖 User Guide & Capture Delay

### ⏱️ Understanding "Capture Delay"
In the toolbar next to the active tabs selector, you will find the **Capture Delay** slider (ranging from **1s to 5s**).

#### Why is Capture Delay necessary?
Modern web applications are dynamic and asynchronous:
1. **Scroll-triggered animations**: Many websites use libraries such as AOS, GSAP, WOW.js, or Framer Motion that trigger fade-in, slide-up, or zoom effects only when scrolled into view.
2. **Lazy-loaded images & iframes**: Images and media using `loading="lazy"` or `IntersectionObserver` require time to request, download, and decode after scrolling.
3. **Dynamic font rendering & web fonts**: Custom web fonts often take a fraction of a second to swap and stabilize layout geometry.
4. **Interactive Single Page Apps (SPAs)**: Content loaded on demand (e.g. charts, social embeds, comments) needs a brief stabilization period.

#### How to use it:
- **Default (2s - 3s)**: Ideal for most standard corporate, blog, or documentation sites.
- **Fast / Static Sites (1s)**: Suitable for simple static HTML pages or dashboards where content is fully rendered immediately.
- **Heavy / Animation-Rich Sites (4s - 5s)**: Recommended for rich landing pages, e-commerce product catalogs, heavy portfolio sites, or slower network connections to ensure all assets are 100% visible before taking the capture.
- **Persistence**: Your selected delay setting is automatically saved to `~/.snapflow/config.json` and will be preserved the next time you open SnapFlow.

---

### 📸 Capture Modes Walkthrough

1. **🖥️ Viewport Capture (`btn_screenshot_viewport`)**:
   - Captures the exact visible area of the active browser tab.
   - Respects the configured delay to ensure any visible hover/focus or transition animations have settled.

2. **📜 Full Page Capture (`btn_screenshot_fullpage`)**:
   - SnapFlow automatically scrolls through the entire webpage to trigger lazy-loaded images, pauses for your configured **Capture Delay**, returns to the top, and takes a seamless, high-definition full-height screenshot.
   - **Fixed Navigation Bar Handling**: Temporarily anchors sticky navigation headers so they don't stretch or duplicate across the page, then automatically restores them to normal once the capture is complete.

3. **📐 Scroll Range Capture (`btn_screenshot_range`)**:
   - **Step 1**: Click "📐 Scroll Capture to Position" at the starting scroll offset.
   - **Step 2**: Scroll down inside the browser window to where you want the screenshot to end.
   - **Step 3**: Click the floating "📸 Confirm Capture" banner in SnapFlow.
   - SnapFlow captures each segment, automatically pauses for the stabilization delay, stitches the pieces together with sub-pixel precision, and eliminates duplicate fixed headers.


---

## 📦 Building Standalone Executables (PyInstaller)

You can package SnapFlow into a standalone executable that does not require Python installed on the target machine:

### 1. Install PyInstaller

```bash
pip install pyinstaller
```

### 2. Build Commands

#### macOS (`.app` / Binary):
```bash
pyinstaller --noconsole --name SnapFlow \
  --icon "images/icon.icns" \
  --paths "src" \
  --add-data "images:images" \
  --add-data "src/i18n:i18n" \
  --add-data "$(.venv/bin/python -c 'import customtkinter, os; print(os.path.dirname(customtkinter.__file__))'):customtkinter" \
  main.py
```

#### Linux Binary:
> On Linux, path separators in `--add-data` use `:` (colon), identical to macOS:
```bash
pyinstaller --noconsole --onefile --name SnapFlow \
  --icon "images/icon.png" \
  --paths "src" \
  --add-data "images:images" \
  --add-data "src/i18n:i18n" \
  --add-data "$(.venv/bin/python -c 'import customtkinter, os; print(os.path.dirname(customtkinter.__file__))'):customtkinter" \
  main.py
```

#### Windows (`.exe`):
> On Windows, path separators in `--add-data` use `;` (semicolon):
```powershell
python -m PyInstaller --noconsole --onefile --name SnapFlow `
  --icon "images/icon.ico" `
  --paths "src" `
  --add-data "images;images" `
  --add-data "src/i18n;i18n" `
  --add-data "$((python -c 'import customtkinter, os; print(os.path.dirname(customtkinter.__file__))'));customtkinter" `
  main.py
```

> **Note regarding Playwright Browsers & macOS Native Frameworks**:
> - When distributing standalone executables, the target machine should either have Google Chrome installed, or you can package Playwright browsers by setting `PLAYWRIGHT_BROWSERS_PATH=0` prior to packaging.
> - On macOS, you can optionally install `pyobjc-framework-Cocoa` before building if you want native Dock icon and system language auto-detection in the standalone bundle.

---

## 📁 Project Architecture

```
SnapFlow/
├── main.py                  # Entry point, CLI argument parsing, sys.path configuration
├── requirements.txt         # Project dependencies
├── README.md                # Project documentation
├── .gitignore               # Git ignore rules
├── images/                  # Application icons (.icns, .ico, .svg, .png)
└── src/                     # Core source code
    ├── app.py               # Main GUI controller, event dispatching, window/dock icon setup
    ├── config_manager.py    # Persistent configuration store (~/.snapflow/config.json)
    ├── browser_manager.py   # Playwright worker thread, active tab tracker, range capture stitching
    ├── screenshot_model.py  # Screenshot data model, ordering, validation, export states
    ├── ui/
    │   ├── __init__.py
    │   ├── toolbar.py       # Top toolbar (browser launch, tabs dropdown, capture triggers, settings, donation)
    │   ├── preview_panel.py # Image preview card, full-width scroll viewer, multi-selection management
    │   ├── export_panel.py  # Export action dock (batch PNG saving, PDF export, selection counts)
    │   └── dialogs.py       # Modal dialogs (LoadingDialog, RenameDialog, ConfirmDeleteDialog, etc.)
    ├── i18n/
    │   ├── __init__.py      # Locale detection, runtime language switcher, cached translation store
    │   ├── en_us.json       # English localization strings
    │   ├── zh_tw.json       # Traditional Chinese localization strings
    │   └── ms_my.json       # Malay localization strings
    └── utils/
        ├── __init__.py
        ├── file_utils.py    # Temp workspace creation, safe path operations, lifecycle cleanup
        └── image_utils.py   # Thumbnail generation, RGB conversions, PDF export, PNG sanitization
```

## ☕ Support

If you find SnapFlow helpful and it saves you time, consider buying me a coffee to support further development and maintenance!

<p>
  <a href="https://buymeacoffee.com/cylee99" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50" style="height: 50px !important;">
  </a>
</p>

# SnapFlow 📸

**SnapFlow** is a modern desktop web screenshot and capture management tool built with **Playwright** and **CustomTkinter**. Designed for users who need to interactively browse websites, perform manual authentication/login, and capture clean, precise screenshots (Viewport, Full Page, or Custom Scroll Range) with intuitive previewing, drag-and-drop reordering, renaming, and batch exporting.

---

## ✨ Features

1. **Headful Browser (Chrome / Edge / Brave / Chromium)**:
   - Click "Launch Browser" to browse freely, log into accounts, and interact with web pages.
   - **Multi-Browser Automatic Fallback**: Seamlessly detects and prioritizes installed browsers: **Google Chrome** ➡️ **Microsoft Edge** ➡️ **Brave Browser** ➡️ **Playwright Chromium**. If you have Edge or Brave installed, you don't even need Chrome or Playwright's browser package!
   - Dynamically tracks the **active tab**, page title, and live URL, allowing tab switching directly via the GUI dropdown menu.
   - Safe shutdown lifecycle: shuts down tabs and contexts gracefully to eliminate process crashes (`SIGTRAP`) on macOS.

2. **Three Capture Modes & Adjustable Delay Slider (1s – 5s)**:
   - **📸 Viewport Capture**: Instantly grabs the currently visible browser screen area.
   - **📑 Full Page Capture**: Automatically scrolls to the very top and captures the entire scrollable webpage in high definition.
   - **📍 Scroll Range Capture (To Position)**:
     - Mark a starting position, scroll down to any target position, and confirm capture.
     - **Smart Sticky Header Handling**: Naturally preserves navigation and search bars at the very top of the page while automatically hiding fixed/sticky elements during subsequent scroll slices to prevent duplicate sticky headers.
     - **High-DPI / Retina Screen Stitching**: Sub-pixel floating-point coordinate alignment and bottom boundary clamping ensure seamless stitching without seams or overlapping lines.
   - **⏱️ Adjustable Capture Delay Slider (1s – 5s)**:
     - Located prominently on the toolbar's capture row, allowing users to freely adjust the stabilization delay from **1 to 5 seconds**.
     - **Why it matters**: Modern websites frequently use scroll-triggered JavaScript animations (e.g., AOS, GSAP, WOW.js) and lazy-loaded images (`IntersectionObserver`). The delay gives external assets, web fonts, and asynchronous network requests sufficient time to render completely before the shot is taken.
     - **Zero Side-Effects**: SnapFlow freezes animations during the capture and immediately restores normal browser rendering via guaranteed cleanup (`finally` block) once the capture finishes.
     - **Auto-Saved Preference**: Your chosen delay value is automatically persisted to `~/.snapflow/config.json` and remembered across app restarts.

3. **Loading Modal & Anti-Spam Protection**:
   - Displays an animated loading modal during screenshot captures, range stitching, and application shutdown.
   - Intercepts and blocks user clicks during operations to prevent duplicate requests or UI freezes.

4. **Preview, Multi-Selection & List Management**:
   - **Full-Width Scrollable Preview**: Renders long full-page screenshots at full readable width, enabling smooth vertical scrolling inspection.
   - **Adaptive List Display & Auto-Scroll**: Dynamically measures available pixel width and fits screenshot titles cleanly, maximizing visible text. Automatically scrolls down to the newest item upon capture so you never miss a shot.
   - **Custom Renaming & Duplicate Detection**: Rename captures on the fly with instant validation and character sanitization.
   - **Single & Multi-Select Operations**:
     - Single item: move up (`▲`), move down (`▼`), or rename (`✏️`).
     - Multi-select: hold `Ctrl` or `Cmd` to select multiple captures for bulk deletion or selective export.
     - Automatically disables move and rename buttons during multi-selection to prevent state desynchronization.
     - Direct mouse **drag-and-drop** reordering.

5. **Flexible Export Options**:
   - **Smart Scope Detection**: Dynamically toggles between "Export All" and "Export Selected" depending on current list selection.
   - **Batch PNG Export**: Saves screenshots as individual PNG images with automatic filename conflict handling.
   - **Merged PDF Export**: Flattens and combines screenshots into a single multi-page PDF document on white backgrounds.

6. **Appearance & Themes**:
   - Seamlessly toggle between **Light**, **Dark**, and **System** appearance modes on the fly.
   - User theme preferences are automatically persisted in `~/.snapflow/config.json`.

7. **Internationalization (i18n)**:
   - Full localization support for **English (`en_us`)**, **Traditional Chinese (`zh_tw`)**, and **Malay (`ms_my`)**.
   - In-memory dictionary caching with dynamic runtime language switching.

8. **Unsaved Changes Safety & Temp Cleanup**:
   - Prompts for confirmation when closing the application with unexported screenshots.
   - Automatically cleans up all temporary screenshot files upon exit to save disk space.

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
# Launch in English with Dark theme
python main.py --lang en_us --theme dark

# Launch in Traditional Chinese
python main.py --lang zh_tw

# Launch in Malay following system appearance mode
python main.py --lang ms_my --theme system
```

**Available CLI Options**:
- `--lang`: `en_us` (English), `zh_tw` (Traditional Chinese), `ms_my` (Malay)
- `--theme`: `light`, `dark`, `system`

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

#### Windows (`.exe`):
```powershell
python -m PyInstaller --noconsole --onefile --name SnapFlow `
  --icon "images/icon.ico" `
  --paths "src" `
  --add-data "images;images" `
  --add-data "src/i18n;i18n" `
  --add-data "$((python -c 'import customtkinter, os; print(os.path.dirname(customtkinter.__file__))'));customtkinter" `
  main.py
```

> **Note regarding Playwright Browsers**:
> When distributing standalone executables, the target machine should either have Google Chrome installed, or you can package Playwright browsers by setting `PLAYWRIGHT_BROWSERS_PATH=0` prior to packaging.

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

<p align="center">
  <a href="https://buymeacoffee.com/cylee99" target="_blank">
    <img src="https://cdn.buymeacoffee.com/buttons/v2/default-yellow.png" alt="Buy Me A Coffee" height="50" style="height: 50px !important;">
  </a>
</p>

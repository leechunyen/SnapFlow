"""Image handling utilities for SnapFlow.

Provides thumbnail generation, PIL conversions, PDF compilation,
and PNG batch export.
"""

from __future__ import annotations

import io
import re
import shutil
from pathlib import Path
from typing import Any, Sequence
from PIL import Image

# Disable Pillow decompression bomb limit to support ultra-long web page captures
Image.MAX_IMAGE_PIXELS = None

THUMBNAIL_MAX_SIZE: tuple[int, int] = (280, 200)


def bytes_to_pil(img_bytes: bytes) -> Image.Image:
    """Converts raw image bytes to a PIL Image instance."""
    return Image.open(io.BytesIO(img_bytes))


def bytes_to_thumbnail(img_bytes: bytes, max_size: tuple[int, int] = THUMBNAIL_MAX_SIZE) -> Image.Image:
    """Creates a thumbnail PIL Image while maintaining aspect ratio."""
    img = bytes_to_pil(img_bytes)
    # Convert to RGBA for consistent display in GUI
    if img.mode not in ("RGB", "RGBA"):
        img = img.convert("RGBA")
    img.thumbnail(max_size, Image.Resampling.LANCZOS)
    return img


def _to_rgb_with_white_bg(img: Image.Image) -> Image.Image:
    """Ensures an image is RGB with a white background for PDF output."""
    if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
        rgba = img.convert("RGBA")
        white_bg = Image.new("RGB", rgba.size, (255, 255, 255))
        white_bg.paste(rgba, mask=rgba.split()[3])
        return white_bg
    return img.convert("RGB")


def export_pdf(filepaths: Sequence[Path | str], output_path: Path | str) -> None:
    """Combines a list of image files into a single multi-page PDF.

    Preserves the given sequence of files.
    """
    if not filepaths:
        raise ValueError("No images provided for PDF export")

    images: list[Image.Image] = []
    try:
        for fp in filepaths:
            path = Path(fp)
            if path.exists():
                with Image.open(path) as raw:
                    rgb_img = _to_rgb_with_white_bg(raw)
                    rgb_img.load()  # Force reading pixel data into memory before raw file handle closes
                    images.append(rgb_img)

        if not images:
            raise ValueError("Could not open any valid image files")

        out_file = Path(output_path)
        out_file.parent.mkdir(parents=True, exist_ok=True)

        first, rest = images[0], images[1:]
        first.save(
            out_file,
            format="PDF",
            resolution=150.0,
            save_all=True,
            append_images=rest,
        )
    finally:
        for img in images:
            try:
                img.close()
            except Exception:
                pass


def sanitize_filename(name: str) -> str:
    """Strips characters invalid in filenames across OSes."""
    cleaned = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return cleaned or "screenshot"


def export_pngs(items: Sequence[Any], dest_dir: Path | str) -> list[Path]:
    """Exports images as PNG files into dest_dir, respecting custom_name if available.

    Accepts a sequence of Screenshot instances or Path/str objects.
    """
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)

    saved_paths: list[Path] = []
    used_names: set[str] = set()
    total = len(items)
    pad = max(2, len(str(total)))

    for idx, item in enumerate(items, start=1):
        # Extract filepath and optional custom_name
        if hasattr(item, "filepath"):
            src = Path(item.filepath)
            custom_name = getattr(item, "custom_name", "") or ""
        else:
            src = Path(item)
            custom_name = ""

        if not src.exists():
            continue

        if custom_name.strip():
            base = sanitize_filename(custom_name)
        elif hasattr(item, "page_title") and getattr(item, "page_title", "").strip():
            base = sanitize_filename(getattr(item, "page_title"))
        else:
            base = f"screenshot_{str(idx).zfill(pad)}"

        # Strip .png if user accidentally entered filename with extension
        if base.lower().endswith(".png"):
            base = base[:-4].strip() or f"screenshot_{str(idx).zfill(pad)}"

        candidate = f"{base}.png"
        collision_counter = 2
        while candidate.lower() in used_names:
            candidate = f"{base}_{collision_counter}.png"
            collision_counter += 1
        used_names.add(candidate.lower())

        target = dest / candidate
        shutil.copy2(src, target)
        saved_paths.append(target)

    return saved_paths

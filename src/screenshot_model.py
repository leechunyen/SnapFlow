"""Data models for managing screenshots in SnapFlow."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class Screenshot:
    """Represents a single screenshot capture."""

    filepath: Path
    label: str = ""
    thumbnail: Any = None  # PIL.Image.Image thumbnail
    page_title: str = ""
    page_url: str = ""
    is_full_page: bool = False
    custom_name: str = ""  # User-defined name for export (without extension)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))


class ScreenshotModel:
    """Manages ordered list of screenshots and export status."""

    def __init__(self) -> None:
        self.shots: list[Screenshot] = []
        self._exported: bool = False

    @property
    def has_unsaved(self) -> bool:
        """True if there are screenshots that have not been exported yet."""
        return len(self.shots) > 0 and not self._exported

    def add(self, shot: Screenshot) -> None:
        """Adds a screenshot and marks the model as unexported."""
        self.shots.append(shot)
        self._exported = False

    def delete(self, index: int) -> Screenshot | None:
        """Deletes a screenshot by index, deletes its temporary file, and marks unexported."""
        if 0 <= index < len(self.shots):
            shot = self.shots.pop(index)
            if shot.filepath and shot.filepath.exists():
                try:
                    shot.filepath.unlink()
                except OSError:
                    pass
            self._exported = False
            return shot
        return None

    def delete_multiple(self, indices: list[int]) -> list[Screenshot]:
        """Deletes multiple screenshots by index (in descending order), unlinks files, and marks unexported."""
        deleted: list[Screenshot] = []
        for idx in sorted(set(indices), reverse=True):
            if 0 <= idx < len(self.shots):
                shot = self.shots.pop(idx)
                if shot.filepath and shot.filepath.exists():
                    try:
                        shot.filepath.unlink()
                    except OSError:
                        pass
                deleted.append(shot)
        if deleted:
            self._exported = False
        return deleted

    def get_shots(self, indices: list[int] | None = None) -> list[Screenshot]:
        """Returns screenshots for the specified indices, or all if None."""
        if indices is None:
            return list(self.shots)
        return [self.shots[i] for i in indices if 0 <= i < len(self.shots)]

    def get_filepaths_by_indices(self, indices: list[int] | None = None) -> list[Path]:
        """Returns filepaths for the specified indices, or all if None."""
        shots = self.get_shots(indices)
        return [s.filepath for s in shots if s.filepath and s.filepath.exists()]

    def move_up(self, index: int) -> bool:
        """Moves screenshot at index up by one position."""
        if 0 < index < len(self.shots):
            self.shots[index], self.shots[index - 1] = self.shots[index - 1], self.shots[index]
            self._exported = False
            return True
        return False

    def move_down(self, index: int) -> bool:
        """Moves screenshot at index down by one position."""
        if 0 <= index < len(self.shots) - 1:
            self.shots[index], self.shots[index + 1] = self.shots[index + 1], self.shots[index]
            self._exported = False
            return True
        return False

    def reorder(self, from_idx: int, to_idx: int) -> bool:
        """Moves item from from_idx to to_idx in the list."""
        if 0 <= from_idx < len(self.shots) and 0 <= to_idx < len(self.shots):
            if from_idx != to_idx:
                item = self.shots.pop(from_idx)
                self.shots.insert(to_idx, item)
                self._exported = False
                return True
        return False

    def is_name_duplicate(self, candidate_name: str, exclude_index: int = -1) -> bool:
        """Checks if another screenshot already uses candidate_name as custom_name or effective export name."""
        target = candidate_name.strip().lower()
        if not target:
            return False
        for idx, shot in enumerate(self.shots):
            if idx == exclude_index:
                continue
            # Compare with custom_name or fallback page_title
            effective_name = (shot.custom_name or shot.page_title or "").strip().lower()
            if effective_name and effective_name == target:
                return True
        return False

    def rename(self, index: int, new_name: str) -> bool:
        """Sets custom name on screenshot at index if valid and not duplicate."""
        if 0 <= index < len(self.shots):
            cleaned = new_name.strip()
            if cleaned and not self.is_name_duplicate(cleaned, exclude_index=index):
                self.shots[index].custom_name = cleaned
                self._exported = False
                return True
        return False

    def mark_exported(self) -> None:
        """Marks current screenshots as having been exported."""
        self._exported = True

    def get_filepaths(self) -> list[Path]:
        """Returns ordered list of existing screenshot file paths."""
        return [s.filepath for s in self.shots if s.filepath and s.filepath.exists()]

    def count(self) -> int:
        """Returns count of screenshots."""
        return len(self.shots)

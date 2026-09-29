import os
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from contracts.files.models import (
    FileActionResult,
    FileActionType,
    FileInfo,
)
from windows_agent.config import settings
from windows_agent.safety import validate_path

# Standard category mapping for folder reorganization
EXTENSION_CATEGORIES: Dict[str, str] = {
    # Documents
    ".pdf": "Documents",
    ".doc": "Documents",
    ".docx": "Documents",
    ".txt": "Documents",
    ".rtf": "Documents",
    ".odt": "Documents",
    ".xlsx": "Documents/Spreadsheets",
    ".xls": "Documents/Spreadsheets",
    ".csv": "Documents/Spreadsheets",
    ".pptx": "Documents/Presentations",
    ".ppt": "Documents/Presentations",
    # Images
    ".png": "Images",
    ".jpg": "Images",
    ".jpeg": "Images",
    ".gif": "Images",
    ".webp": "Images",
    ".svg": "Images",
    ".bmp": "Images",
    ".ico": "Images",
    # Audio & Video
    ".mp4": "Videos",
    ".mkv": "Videos",
    ".mov": "Videos",
    ".avi": "Videos",
    ".webm": "Videos",
    ".mp3": "Audio",
    ".wav": "Audio",
    ".flac": "Audio",
    ".m4a": "Audio",
    # Archives & Installers
    ".zip": "Archives",
    ".rar": "Archives",
    ".7z": "Archives",
    ".tar": "Archives",
    ".gz": "Archives",
    ".exe": "Installers",
    ".msi": "Installers",
    # Code & Data
    ".py": "Code",
    ".json": "Data",
    ".yaml": "Data",
    ".yml": "Data",
    ".sql": "Data",
}


class FileTools:
    def __init__(self, allowed_roots: Optional[List[Path]] = None) -> None:
        self.allowed_roots = allowed_roots or settings.get_allowed_roots()

    def list_directory(
        self,
        directory_path: str | Path,
        recursive: bool = False,
        max_items: int = 300,
    ) -> List[FileInfo]:
        """Lists files and folders within a validated directory path."""
        target_dir = validate_path(directory_path, self.allowed_roots)
        if not target_dir.exists():
            raise FileNotFoundError(f"Directory not found: '{target_dir}'")
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: '{target_dir}'")

        items: List[FileInfo] = []
        iterator = target_dir.rglob("*") if recursive else target_dir.iterdir()

        for entry in iterator:
            if len(items) >= max_items:
                break
            try:
                stat = entry.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                items.append(
                    FileInfo(
                        name=entry.name,
                        path=str(entry.resolve()),
                        is_directory=entry.is_dir(),
                        size_bytes=stat.st_size if entry.is_file() else 0,
                        modified_at=mod_time,
                    )
                )
            except (PermissionError, OSError):
                continue

        return items

    def search_files(
        self,
        directory_path: str | Path,
        pattern: str,
        recursive: bool = True,
        max_results: int = 150,
    ) -> List[FileInfo]:
        """Searches for files matching a glob pattern (e.g. *.pdf) within a validated path."""
        target_dir = validate_path(directory_path, self.allowed_roots)
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Search target is not a directory: '{target_dir}'")

        results: List[FileInfo] = []
        matcher = target_dir.rglob(pattern) if recursive else target_dir.glob(pattern)

        for entry in matcher:
            if len(results) >= max_results:
                break
            try:
                stat = entry.stat()
                mod_time = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                results.append(
                    FileInfo(
                        name=entry.name,
                        path=str(entry.resolve()),
                        is_directory=entry.is_dir(),
                        size_bytes=stat.st_size if entry.is_file() else 0,
                        modified_at=mod_time,
                    )
                )
            except (PermissionError, OSError):
                continue

        return results

    def preview_organize(
        self,
        directory_path: str | Path,
        strategy: str = "by_extension",
    ) -> Dict[str, Any]:
        """
        Calculates a dry-run preview of planned file movements without touching files on disk.
        """
        target_dir = validate_path(directory_path, self.allowed_roots)
        if not target_dir.is_dir():
            raise NotADirectoryError(f"Target is not a directory: '{target_dir}'")

        planned_moves: List[Dict[str, str]] = []
        categories_found: Dict[str, int] = {}

        # Only organize top-level files in the target directory (not subfolders)
        for entry in target_dir.iterdir():
            if not entry.is_file():
                continue

            ext = entry.suffix.lower()
            category = EXTENSION_CATEGORIES.get(ext, "Other")
            dest_dir = target_dir / category
            dest_file = dest_dir / entry.name

            planned_moves.append({
                "source": str(entry.resolve()),
                "destination": str(dest_file.resolve()),
                "filename": entry.name,
                "category": category,
            })
            categories_found[category] = categories_found.get(category, 0) + 1

        return {
            "directory": str(target_dir),
            "strategy": strategy,
            "total_files": len(planned_moves),
            "categories": categories_found,
            "planned_moves": planned_moves,
        }

    def move_file(
        self,
        source_path: str | Path,
        destination_path: str | Path,
        overwrite: bool = False,
    ) -> FileActionResult:
        """Moves a single file safely after validating both source and destination."""
        src = validate_path(source_path, self.allowed_roots)
        if not src.exists():
            raise FileNotFoundError(f"Source file does not exist: '{src}'")
        if not src.is_file():
            raise ValueError(f"Source path is not a file: '{src}'")

        dest = validate_path(destination_path, self.allowed_roots)

        # If destination is an existing directory, target is dest / src.name
        if dest.is_dir():
            dest = dest / src.name

        if dest.exists() and not overwrite:
            raise FileExistsError(f"Destination already exists and overwrite=False: '{dest}'")

        # Create parent directory if needed
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))

        return FileActionResult(
            action=FileActionType.MOVE_FILE,
            success=True,
            message=f"Moved '{src.name}' to '{dest}'",
            affected_count=1,
            details={"source": str(src), "destination": str(dest)},
        )

    def execute_organize(
        self,
        directory_path: str | Path,
        strategy: str = "by_extension",
    ) -> FileActionResult:
        """Executes the folder organization moves."""
        preview = self.preview_organize(directory_path, strategy=strategy)
        planned_moves = preview["planned_moves"]

        moved_count = 0
        errors: List[str] = []

        for move in planned_moves:
            try:
                self.move_file(move["source"], move["destination"], overwrite=False)
                moved_count += 1
            except Exception as e:
                errors.append(f"Failed to move {move['filename']}: {str(e)}")

        return FileActionResult(
            action=FileActionType.ORGANIZE_FOLDER,
            success=len(errors) == 0,
            message=f"Organized {moved_count} of {len(planned_moves)} files.",
            affected_count=moved_count,
            details={"moved_count": moved_count, "errors": errors, "directory": str(directory_path)},
        )


file_tools = FileTools()

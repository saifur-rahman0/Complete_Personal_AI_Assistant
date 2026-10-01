import os
import re
import shutil
import subprocess
import sys
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
        self._allowed_roots = allowed_roots

    @property
    def allowed_roots(self) -> List[Path]:
        if self._allowed_roots is not None:
            return self._allowed_roots
        return settings.get_allowed_roots()

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
        directory_path: Optional[str | Path] = None,
        pattern: str = "*",
        recursive: bool = True,
        max_results: int = 150,
    ) -> List[FileInfo]:
        """Searches for files matching keywords or glob pattern within validated path(s)."""
        # 1. Resolve search root directories (fallback to allowed roots if not specified)
        search_dirs: List[Path] = []
        if directory_path and str(directory_path).strip():
            target_dir = validate_path(directory_path, self.allowed_roots)
            if not target_dir.is_dir():
                raise NotADirectoryError(f"Search target is not a directory: '{target_dir}'")
            search_dirs = [target_dir]
        else:
            search_dirs = [r for r in self.allowed_roots if r.is_dir()]

        # 2. Parse search pattern for keywords and required extension
        clean = (pattern or "*").strip().lower()
        required_ext: Optional[str] = None
        keywords: List[str] = []

        # Check for extension like *.pdf or "pdf"
        ext_match = re.search(r"\*?\.([a-zA-Z0-9]+)\b", clean)
        if ext_match:
            required_ext = f".{ext_match.group(1).lower()}"
            clean = re.sub(r"\*?\.[a-zA-Z0-9]+\b", "", clean)

        for token in clean.replace("*", " ").split():
            token = token.strip()
            if token in ("files", "file", "all", "any", "present", "there", "in", "from", "on"):
                continue
            if token in ("pdf", "docx", "doc", "txt", "xlsx", "xls", "png", "jpg", "jpeg", "zip", "exe", "py", "json"):
                required_ext = f".{token}"
            elif len(token) >= 2:
                keywords.append(token)

        results: List[FileInfo] = []
        seen_paths = set()

        for s_dir in search_dirs:
            if len(results) >= max_results:
                break
            iterator = s_dir.rglob("*") if recursive else s_dir.iterdir()
            for entry in iterator:
                if len(results) >= max_results:
                    break
                try:
                    entry_path_str = str(entry.resolve())
                    if entry_path_str in seen_paths:
                        continue

                    # Filter: if looking for files, skip directories
                    if entry.is_dir() and (required_ext or keywords):
                        continue

                    entry_name_lower = entry.name.lower()

                    # Check extension match
                    if required_ext and not entry_name_lower.endswith(required_ext):
                        continue

                    # Check keyword terms match (substring in filename)
                    if keywords:
                        if not all(kw in entry_name_lower for kw in keywords):
                            continue

                    seen_paths.add(entry_path_str)
                    stat = entry.stat()
                    mod_time = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                    results.append(
                        FileInfo(
                            name=entry.name,
                            path=entry_path_str,
                            is_directory=entry.is_dir(),
                            size_bytes=stat.st_size if entry.is_file() else 0,
                            modified_at=mod_time,
                        )
                    )
                except (PermissionError, OSError):
                    continue

        return results

    def read_file_content(
        self,
        file_path: str | Path,
        max_bytes: int = 15000,
    ) -> Dict[str, Any]:
        """Safely reads preview content of a text or document file."""
        target_file = validate_path(file_path, self.allowed_roots)
        if not target_file.is_file():
            raise FileNotFoundError(f"File not found: '{target_file}'")

        try:
            stat = target_file.stat()
            size = stat.st_size
            with open(target_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read(max_bytes)

            truncated = size > max_bytes
            return {
                "name": target_file.name,
                "path": str(target_file.resolve()),
                "size_bytes": size,
                "content": content,
                "truncated": truncated,
            }
        except Exception as e:
            raise OSError(f"Could not read file content: {e}")

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

    def open_file(
        self,
        file_path: str | Path,
        reveal: bool = False,
    ) -> FileActionResult:
        """Opens or reveals a file or folder safely."""
        target = validate_path(file_path, self.allowed_roots)
        if not target.exists():
            raise FileNotFoundError(f"Target path does not exist: '{target}'")

        if sys.platform == "win32":
            if reveal:
                subprocess.Popen(["explorer.exe", f"/select,{str(target)}"])
            else:
                os.startfile(str(target))
        else:
            subprocess.Popen(["xdg-open", str(target)])

        return FileActionResult(
            action=FileActionType.OPEN_FILE,
            success=True,
            message=f"{'Revealed' if reveal else 'Opened'} '{target.name}'",
            affected_count=1,
            details={"path": str(target), "revealed": reveal},
        )

    def rename_file(
        self,
        file_path: str | Path,
        new_name: str,
    ) -> FileActionResult:
        """Renames a file safely within its current parent directory."""
        src = validate_path(file_path, self.allowed_roots)
        if not src.exists():
            raise FileNotFoundError(f"Source file does not exist: '{src}'")

        # Sanitize new_name to prevent directory traversal in name
        clean_name = Path(new_name).name
        if not clean_name or clean_name in (".", ".."):
            raise ValueError(f"Invalid new file name: '{new_name}'")

        dest = src.parent / clean_name
        dest = validate_path(dest, self.allowed_roots)

        if dest.exists() and dest != src:
            raise FileExistsError(f"A file named '{clean_name}' already exists in '{src.parent}'")

        src.rename(dest)
        return FileActionResult(
            action=FileActionType.RENAME_FILE,
            success=True,
            message=f"Renamed '{src.name}' to '{clean_name}'",
            affected_count=1,
            details={"old_path": str(src), "new_path": str(dest), "new_name": clean_name},
        )

    def delete_file(
        self,
        file_path: str | Path,
        permanent: bool = False,
    ) -> FileActionResult:
        """Safely deletes or sends a file to the Recycle Bin."""
        target = validate_path(file_path, self.allowed_roots)
        if not target.exists():
            raise FileNotFoundError(f"Target file does not exist: '{target}'")

        target_name = target.name
        is_dir = target.is_dir()

        if not permanent:
            try:
                import send2trash
                send2trash.send2trash(str(target))
                msg = f"Moved '{target_name}' to Recycle Bin."
            except Exception:
                if is_dir:
                    shutil.rmtree(str(target))
                else:
                    target.unlink()
                msg = f"Deleted '{target_name}'."
        else:
            if is_dir:
                shutil.rmtree(str(target))
            else:
                target.unlink()
            msg = f"Permanently deleted '{target_name}'."

        return FileActionResult(
            action=FileActionType.DELETE_FILE,
            success=True,
            message=msg,
            affected_count=1,
            details={"deleted_path": str(target), "permanent": permanent},
        )


file_tools = FileTools()

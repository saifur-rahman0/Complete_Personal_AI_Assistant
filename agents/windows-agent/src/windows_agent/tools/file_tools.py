import difflib
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from contracts.files.models import (
    FileActionResult,
    FileActionType,
    FileInfo,
)
from windows_agent.config import settings
from windows_agent.safety import validate_path

EXTENSION_CATEGORIES: Dict[str, str] = {
    ".pdf": "Documents", ".doc": "Documents", ".docx": "Documents", ".txt": "Documents",
    ".xlsx": "Documents/Spreadsheets", ".xls": "Documents/Spreadsheets", ".csv": "Documents/Spreadsheets",
    ".pptx": "Documents/Presentations", ".ppt": "Documents/Presentations",
    ".png": "Images", ".jpg": "Images", ".jpeg": "Images", ".gif": "Images", ".webp": "Images",
    ".mp4": "Videos", ".mkv": "Videos", ".mov": "Videos", ".avi": "Videos",
    ".mp3": "Audio", ".wav": "Audio", ".flac": "Audio",
    ".zip": "Archives", ".rar": "Archives", ".7z": "Archives",
    ".exe": "Installers", ".msi": "Installers",
    ".py": "Code", ".json": "Data",
}

CATEGORY_EXTENSIONS: Dict[str, List[str]] = {
    "image": [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"],
    "images": [".png", ".jpg", ".jpeg", ".webp", ".gif", ".bmp", ".svg"],
    "photo": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "photos": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "picture": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "pictures": [".png", ".jpg", ".jpeg", ".webp", ".gif"],
    "video": [".mp4", ".mkv", ".mov", ".avi", ".webm"],
    "videos": [".mp4", ".mkv", ".mov", ".avi", ".webm"],
    "movie": [".mp4", ".mkv", ".mov", ".avi", ".webm"],
    "audio": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
    "music": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
    "song": [".mp3", ".wav", ".flac", ".m4a", ".aac"],
    "document": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
    "documents": [".pdf", ".docx", ".doc", ".txt", ".xlsx", ".pptx"],
    "doc": [".docx", ".doc", ".pdf", ".txt"],
    "pdf": [".pdf"],
    "sheet": [".xlsx", ".xls", ".csv"],
    "sheets": [".xlsx", ".xls", ".csv"],
    "presentation": [".pptx", ".ppt"],
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
        category_exts: List[str] = []
        keywords: List[str] = []

        # Check for explicit extension like *.pdf or "pdf"
        ext_match = re.search(r"\*?\.([a-zA-Z0-9]+)\b", clean)
        if ext_match:
            required_ext = f".{ext_match.group(1).lower()}"
            clean = re.sub(r"\*?\.[a-zA-Z0-9]+\b", "", clean)

        # Stop words to ignore during file search
        stop_words = {
            "files", "file", "all", "any", "present", "there", "in", "from",
            "on", "is", "do", "we", "have", "check", "find", "search",
            "show", "me", "get", "look", "locate", "where", "what"
        }

        for token in clean.replace("*", " ").split():
            token = token.strip()
            if token in stop_words:
                continue
            if token in CATEGORY_EXTENSIONS:
                category_exts.extend(CATEGORY_EXTENSIONS[token])
            if token in ("pdf", "docx", "doc", "txt", "xlsx", "xls", "png", "jpg", "jpeg", "zip", "exe", "py", "json"):
                required_ext = f".{token}"
            elif len(token) >= 2:
                keywords.append(token)

        category_exts = list(set(category_exts))

        scored_entries: List[Tuple[float, FileInfo]] = []
        recent_fallback: List[FileInfo] = []
        seen_paths = set()

        for s_dir in search_dirs:
            iterator = s_dir.rglob("*") if recursive else s_dir.iterdir()
            for entry in iterator:
                try:
                    entry_path_str = str(entry.resolve())
                    if entry_path_str in seen_paths:
                        continue
                    if entry.is_dir() and (required_ext or category_exts or keywords):
                        continue

                    entry_name_lower = entry.name.lower()
                    entry_ext = entry.suffix.lower()

                    # Exact extension filter if explicitly requested (e.g. *.pdf)
                    if required_ext and entry_ext != required_ext:
                        continue

                    seen_paths.add(entry_path_str)
                    stat = entry.stat()
                    mod_time = datetime.fromtimestamp(stat.st_mtime, timezone.utc)
                    file_info = FileInfo(
                        name=entry.name,
                        path=entry_path_str,
                        is_directory=entry.is_dir(),
                        size_bytes=stat.st_size if entry.is_file() else 0,
                        modified_at=mod_time,
                    )
                    recent_fallback.append(file_info)

                    # Calculate fuzzy matching score
                    matches_category = entry_ext in category_exts if category_exts else False

                    if not keywords:
                        if matches_category or required_ext:
                            score = 1.0
                        else:
                            score = 0.5
                    else:
                        file_tokens = [t for t in re.split(r"[\s._\-()]+", entry_name_lower) if len(t) >= 2]
                        matched_kw_count = 0

                        for kw in keywords:
                            # 1. Exact substring match in full filename
                            if kw in entry_name_lower:
                                matched_kw_count += 1
                                continue
                            # 2. Fuzzy similarity match against tokens (handles typos like 'genereted' -> 'generated')
                            token_match = False
                            for ft in file_tokens:
                                if difflib.SequenceMatcher(None, kw, ft).ratio() >= 0.72:
                                    token_match = True
                                    break
                            if token_match:
                                matched_kw_count += 1

                        score = matched_kw_count / len(keywords)
                        if matches_category:
                            score += 0.25

                    # Threshold for inclusion
                    min_thresh = 0.45 if len(keywords) >= 2 else (0.8 if keywords else 0.0)
                    if score >= min_thresh or (matches_category and score > 0.0):
                        scored_entries.append((score, file_info))

                except (PermissionError, OSError):
                    continue

        # Sort by relevance score descending, then by newest modification time
        scored_entries.sort(
            key=lambda x: (x[0], x[1].modified_at or datetime.min.replace(tzinfo=timezone.utc)),
            reverse=True,
        )
        results = [x[1] for x in scored_entries[:max_results]]

        # Fallback to the 20 most recent files if no match was found
        if not results and recent_fallback:
            recent_fallback.sort(
                key=lambda x: x.modified_at or datetime.min.replace(tzinfo=timezone.utc),
                reverse=True,
            )
            results = recent_fallback[:20]

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

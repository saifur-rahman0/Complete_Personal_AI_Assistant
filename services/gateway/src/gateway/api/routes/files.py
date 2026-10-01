import logging
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from contracts.files.models import (
    DeleteFileRequest,
    MoveFileRequest,
    OpenFileRequest,
    ReadFileRequest,
    RenameFileRequest,
)

logger = logging.getLogger("gateway.api.files")
router = APIRouter(prefix="/api/v1/files", tags=["files"])

DANGEROUS_SYSTEM_PATHS = [
    Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve(),
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")).resolve(),
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")).resolve(),
    Path(os.environ.get("ProgramData", r"C:\ProgramData")).resolve(),
]


def _validate_safe_path(path_str: str) -> Path:
    if not path_str or not path_str.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Path cannot be empty.",
        )

    target = Path(path_str).resolve()

    # Reject drive roots (e.g. C:\ or /)
    if target.parent == target or target == target.anchor:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Access to root drive '{target}' is forbidden.",
        )

    # Reject system directories
    for dangerous in DANGEROUS_SYSTEM_PATHS:
        try:
            if target == dangerous or target.is_relative_to(dangerous):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access to critical system path '{target}' is forbidden.",
                )
        except AttributeError:
            if str(target).lower().startswith(str(dangerous).lower()):
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Access to critical system path '{target}' is forbidden.",
                )

    return target


@router.post("/open", summary="Open or reveal a file/folder in Windows Explorer")
def open_path(req: OpenFileRequest):
    target = _validate_safe_path(req.path)
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path '{target}' does not exist on workstation.",
        )

    try:
        if sys.platform == "win32":
            if req.reveal:
                subprocess.Popen(["explorer.exe", f"/select,{str(target)}"])
            else:
                os.startfile(str(target))
        else:
            subprocess.Popen(["xdg-open", str(target)])

        return {
            "status": "success",
            "path": str(target),
            "revealed": req.reveal,
            "message": f"Successfully opened '{target.name}'.",
        }
    except Exception as e:
        logger.error(f"Error opening file '{target}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to open path: {str(e)}",
        )


@router.post("/read", summary="Preview text content of a file")
def read_file(req: ReadFileRequest):
    target = _validate_safe_path(req.file_path)
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{target}' does not exist.",
        )
    if not target.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Path '{target}' is a directory, not a file.",
        )

    try:
        size = target.stat().st_size
        max_bytes = min(req.max_bytes, 100000)
        with open(target, "r", encoding="utf-8", errors="replace") as f:
            content = f.read(max_bytes)

        return {
            "status": "success",
            "name": target.name,
            "path": str(target),
            "size_bytes": size,
            "content": content,
            "truncated": size > max_bytes,
        }
    except Exception as e:
        logger.error(f"Error reading file '{target}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to read file: {str(e)}",
        )


@router.post("/rename", summary="Rename a file in place")
def rename_file(req: RenameFileRequest):
    target = _validate_safe_path(req.file_path)
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target file '{target}' does not exist.",
        )

    clean_name = Path(req.new_name).name
    if not clean_name or clean_name in (".", ".."):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid new file name '{req.new_name}'.",
        )

    dest = target.parent / clean_name
    _validate_safe_path(str(dest))

    if dest.exists() and dest != target:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"A file named '{clean_name}' already exists in '{target.parent}'.",
        )

    try:
        target.rename(dest)
        return {
            "status": "success",
            "old_path": str(target),
            "new_path": str(dest),
            "new_name": clean_name,
            "message": f"Successfully renamed '{target.name}' to '{clean_name}'.",
        }
    except Exception as e:
        logger.error(f"Error renaming '{target}' to '{clean_name}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to rename file: {str(e)}",
        )


@router.post("/move", summary="Move a file to a new directory")
def move_file(req: MoveFileRequest):
    src = _validate_safe_path(req.source_path)
    if not src.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source file '{src}' does not exist.",
        )
    if not src.is_file():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Source '{src}' is not a file.",
        )

    dest = _validate_safe_path(req.destination_path)
    if dest.is_dir():
        dest = dest / src.name

    if dest.exists() and not req.overwrite:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Destination '{dest}' already exists and overwrite is False.",
        )

    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src), str(dest))
        return {
            "status": "success",
            "source": str(src),
            "destination": str(dest),
            "message": f"Moved '{src.name}' to '{dest}'.",
        }
    except Exception as e:
        logger.error(f"Error moving file '{src}' to '{dest}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to move file: {str(e)}",
        )


@router.post("/delete", summary="Safely recycle or delete a file")
def delete_file(req: DeleteFileRequest):
    target = _validate_safe_path(req.file_path)
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"File '{target}' does not exist.",
        )

    target_name = target.name
    is_dir = target.is_dir()

    try:
        if not req.permanent:
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

        return {
            "status": "success",
            "path": str(target),
            "message": msg,
        }
    except Exception as e:
        logger.error(f"Error deleting file '{target}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete file: {str(e)}",
        )

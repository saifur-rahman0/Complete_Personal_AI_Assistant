import logging
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger("gateway.api.files")
router = APIRouter(prefix="/api/v1/files", tags=["files"])


class OpenPathRequest(BaseModel):
    path: str = Field(..., description="Absolute or validated path on the host to open or reveal")
    reveal: bool = Field(default=True, description="If true, reveals in File Explorer; if false, opens directly")


@router.post("/open", summary="Open or reveal a file/folder in Windows Explorer")
def open_path(req: OpenPathRequest):
    target = Path(req.path).resolve()
    if not target.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Path '{target}' does not exist on workstation.",
        )

    try:
        if sys.platform == "win32":
            if req.reveal:
                # Open Windows Explorer and select the specific file/folder
                subprocess.Popen(["explorer.exe", f"/select,{str(target)}"])
            else:
                # Open with default application or open directory
                os.startfile(str(target))
        else:
            # Fallback for cross-platform / POSIX
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

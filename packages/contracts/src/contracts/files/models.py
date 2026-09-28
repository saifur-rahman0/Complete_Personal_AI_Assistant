from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileActionType(str, Enum):
    LIST_DIRECTORY = "list_directory"
    SEARCH_FILES = "search_files"
    MOVE_FILE = "move_file"
    ORGANIZE_FOLDER = "organize_folder"


class FileInfo(BaseModel):
    name: str = Field(...)
    path: str = Field(...)
    is_directory: bool = Field(default=False)
    size_bytes: int = Field(default=0)
    modified_at: Optional[datetime] = None


class ListDirectoryRequest(BaseModel):
    directory_path: str = Field(..., description="Target directory path on host")
    recursive: bool = Field(default=False)


class SearchFilesRequest(BaseModel):
    directory_path: str = Field(..., description="Directory to search within")
    pattern: str = Field(..., description="Filename search pattern, e.g. *.pdf")
    recursive: bool = Field(default=True)


class MoveFileRequest(BaseModel):
    source_path: str = Field(..., description="Absolute path of source file")
    destination_path: str = Field(..., description="Absolute destination file or directory path")
    overwrite: bool = Field(default=False)


class OrganizeFolderRequest(BaseModel):
    directory_path: str = Field(..., description="Folder to organize, e.g. Downloads")
    strategy: str = Field(default="by_extension", description="Organize strategy: by_extension, by_date")
    dry_run: bool = Field(default=True, description="If True, preview planned moves without executing")


class FileActionResult(BaseModel):
    action: FileActionType = Field(...)
    success: bool = Field(...)
    message: str = Field(...)
    affected_count: int = Field(default=0)
    details: Dict[str, Any] = Field(default_factory=dict)

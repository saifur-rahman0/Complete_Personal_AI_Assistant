from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class FileActionType(str, Enum):
    LIST_DIRECTORY = "list_directory"
    SEARCH_FILES = "search_files"
    READ_FILE = "read_file"
    OPEN_FILE = "open_file"
    MOVE_FILE = "move_file"
    RENAME_FILE = "rename_file"
    DELETE_FILE = "delete_file"
    ORGANIZE_FOLDER = "organize_folder"


class FileInfo(BaseModel):
    name: str = Field(...)
    path: str = Field(...)
    is_directory: bool = Field(default=False)
    size_bytes: int = Field(default=0)
    modified_at: Optional[datetime] = None


class ListDirectoryRequest(BaseModel):
    directory_path: Optional[str] = Field(default=None, description="Target directory path on host")
    recursive: bool = Field(default=False)


class SearchFilesRequest(BaseModel):
    directory_path: Optional[str] = Field(default=None, description="Directory to search within")
    pattern: str = Field(default="*", description="Filename search pattern, e.g. *.pdf")
    recursive: bool = Field(default=True)


class ReadFileRequest(BaseModel):
    file_path: str = Field(..., description="Absolute path of file to preview")
    max_bytes: int = Field(default=15000, description="Maximum bytes to read")


class OpenFileRequest(BaseModel):
    path: str = Field(..., description="Absolute path of file or folder to open")
    reveal: bool = Field(default=False, description="Whether to reveal in Explorer instead of opening")


class RenameFileRequest(BaseModel):
    file_path: str = Field(..., description="Target file path to rename")
    new_name: str = Field(..., description="New file name with extension")


class MoveFileRequest(BaseModel):
    source_path: str = Field(..., description="Absolute path of source file")
    destination_path: str = Field(..., description="Absolute destination file or directory path")
    overwrite: bool = Field(default=False)


class DeleteFileRequest(BaseModel):
    file_path: str = Field(..., description="Absolute path of file to delete")
    permanent: bool = Field(default=False, description="If True, delete permanently; otherwise move to Recycle Bin")


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

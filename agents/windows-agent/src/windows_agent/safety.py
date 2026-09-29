import os
from pathlib import Path
from typing import List, Optional

DANGEROUS_SYSTEM_PATHS = [
    Path(os.environ.get("SystemRoot", r"C:\Windows")).resolve(),
    Path(os.environ.get("ProgramFiles", r"C:\Program Files")).resolve(),
    Path(os.environ.get("ProgramFiles(x86)", r"C:\Program Files (x86)")).resolve(),
    Path(os.environ.get("ProgramData", r"C:\ProgramData")).resolve(),
]


class SecurityValidationError(PermissionError):
    """Raised when an operation targets an unauthorized or dangerous path."""
    pass


def validate_path(path: str | Path, allowed_roots: List[Path]) -> Path:
    """
    Validates that a path is safe and strictly contained within permitted root directories.
    Resolves symlinks, normalizes traversal (e.g. '..'), and checks forbidden system directories.
    """
    if not path:
        raise SecurityValidationError("Path cannot be empty.")

    target = Path(path).resolve()

    # Reject drive roots (e.g. 'C:\' or 'D:\')
    if target.parent == target or target == target.anchor:
        raise SecurityValidationError(f"Access to root drive '{target}' is strictly forbidden.")

    # Check against known dangerous Windows system directories
    for dangerous in DANGEROUS_SYSTEM_PATHS:
        try:
            if target == dangerous or target.is_relative_to(dangerous):
                raise SecurityValidationError(f"Access to critical system path '{target}' is strictly forbidden.")
        except AttributeError:
            # Python < 3.9 fallback, though requires-python >= 3.10
            if str(target).lower().startswith(str(dangerous).lower()):
                raise SecurityValidationError(f"Access to critical system path '{target}' is strictly forbidden.")

    # Check if target is inside at least one allowed root
    is_allowed = False
    for root in allowed_roots:
        resolved_root = root.resolve()
        try:
            if target == resolved_root or target.is_relative_to(resolved_root):
                is_allowed = True
                break
        except AttributeError:
            if str(target).lower().startswith(str(resolved_root).lower()):
                is_allowed = True
                break

    if not is_allowed:
        allowed_str = ", ".join(str(r) for r in allowed_roots)
        raise SecurityValidationError(
            f"Path '{target}' is outside allowed directories: [{allowed_str}]"
        )

    return target


def is_safe_path(path: str | Path, allowed_roots: List[Path]) -> bool:
    """Helper returning boolean without raising exception."""
    try:
        validate_path(path, allowed_roots)
        return True
    except SecurityValidationError:
        return False

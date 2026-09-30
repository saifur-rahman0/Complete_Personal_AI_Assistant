import logging
import os
import shutil
import subprocess
from typing import Dict, List, Optional
from contracts.desktop.models import DesktopActionResult, DesktopActionType

logger = logging.getLogger("windows_agent.tools.app")

# Strict, non-negotiable application allowlist
APPROVED_APPLICATIONS: Dict[str, List[str]] = {
    "notepad": ["notepad.exe"],
    "calculator": ["calc.exe"],
    "calc": ["calc.exe"],
    "code": ["code.cmd", "code.exe"],
    "vscode": ["code.cmd", "code.exe"],
    "explorer": ["explorer.exe"],
    "taskmgr": ["taskmgr.exe"],
    "edge": ["msedge.exe"],
    "terminal": ["wt.exe", "powershell.exe"],
}


class AppTools:
    """
    Safely launches and controls desktop applications from a strictly verified allowlist.
    Prevents command injection and execution of arbitrary binaries.
    """

    def __init__(self, allowlist: Optional[Dict[str, List[str]]] = None) -> None:
        self.allowlist = allowlist or APPROVED_APPLICATIONS

    def resolve_application_binary(self, app_name: str) -> str:
        """
        Validates app_name against the allowlist and resolves its absolute executable path.
        Raises ValueError if the application is not approved.
        """
        normalized_name = app_name.strip().lower()
        candidates = self.allowlist.get(normalized_name)

        if not candidates:
            raise ValueError(
                f"Application '{app_name}' is not in the approved desktop allowlist. "
                f"Approved applications: {list(self.allowlist.keys())}"
            )

        for candidate in candidates:
            resolved = shutil.which(candidate)
            if resolved:
                return resolved

        # Fallback to candidate binary name if on Windows system path
        return candidates[0]

    def launch_app(self, app_name: str, arguments: Optional[List[str]] = None) -> DesktopActionResult:
        """Launches an approved desktop application safely without shell interpretation."""
        binary_path = self.resolve_application_binary(app_name)
        safe_args = arguments or []

        # Validate arguments to prevent flag abuse
        for arg in safe_args:
            if ";" in arg or "&" in arg or "|" in arg:
                raise ValueError(f"Dangerous character in application argument: '{arg}'")

        cmd = [binary_path] + safe_args
        logger.info(f"Launching approved application: {cmd}")

        try:
            proc = subprocess.Popen(
                cmd,
                shell=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return DesktopActionResult(
                action=DesktopActionType.APP_LAUNCH,
                status="success",
                message=f"Application '{app_name}' launched successfully (PID: {proc.pid}).",
                data={"pid": proc.pid, "executable": binary_path},
            )
        except Exception as e:
            logger.error(f"Failed to launch '{app_name}': {e}")
            return DesktopActionResult(
                action=DesktopActionType.APP_LAUNCH,
                status="failed",
                message=f"Failed to launch application '{app_name}': {str(e)}",
            )

    def close_app(self, target: str, force: bool = False) -> DesktopActionResult:
        """
        Safely closes an approved desktop application by process name or window title.
        Restricted to approved applications to prevent terminating arbitrary system processes.
        """
        normalized_target = target.strip().lower()

        # Check if the target is in the allowlist
        is_approved = any(
            normalized_target in key or any(normalized_target in c.lower() for c in candidates)
            for key, candidates in self.allowlist.items()
        )

        if not is_approved:
            raise ValueError(
                f"Target application '{target}' is not an approved controllable app. "
                f"Allowed applications: {list(self.allowlist.keys())}"
            )

        # On Windows, use taskkill targeting the specific image name
        image_name = (
            normalized_target if normalized_target.endswith(".exe") else f"{normalized_target}.exe"
        )
        cmd = ["taskkill", "/IM", image_name]
        if force:
            cmd.append("/F")

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5.0,
                shell=False,
            )
            if result.returncode == 0:
                return DesktopActionResult(
                    action=DesktopActionType.APP_CLOSE,
                    status="success",
                    message=f"Application '{target}' was closed successfully.",
                    data={"output": result.stdout.strip()},
                )
            else:
                return DesktopActionResult(
                    action=DesktopActionType.APP_CLOSE,
                    status="failed",
                    message=f"Could not close '{target}': {result.stderr.strip() or 'Process not found.'}",
                )
        except Exception as e:
            return DesktopActionResult(
                action=DesktopActionType.APP_CLOSE,
                status="failed",
                message=f"Error closing '{target}': {str(e)}",
            )


app_tools = AppTools()

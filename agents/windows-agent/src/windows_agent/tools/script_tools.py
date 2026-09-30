import logging
import platform
import subprocess
from typing import Any, Dict, List
from contracts.desktop.models import (
    AllowlistedCommandType,
    DesktopActionResult,
    DesktopActionType,
)

logger = logging.getLogger("windows_agent.tools.scripts")

# Exact, immutable command specifications — no dynamic shell construction
ALLOWED_SYSTEM_COMMANDS: Dict[AllowlistedCommandType, List[str]] = {
    AllowlistedCommandType.GET_IP_CONFIG: ["ipconfig"],
    AllowlistedCommandType.GET_WIFI_STATUS: ["netsh", "wlan", "show", "interfaces"],
    AllowlistedCommandType.GET_DISK_SPACE: ["wmic", "logicaldisk", "get", "size,freespace,caption"],
    AllowlistedCommandType.GET_SYSTEM_INFO: ["systeminfo"],
    AllowlistedCommandType.FLUSH_DNS: ["ipconfig", "/flushdns"],
}


class ScriptTools:
    """
    Executes approved, deterministic system inspection and administration commands.
    In strict compliance with AGENTS.md, arbitrary command execution is completely blocked.
    """

    def __init__(self) -> None:
        self.is_windows = platform.system() == "Windows"

    def execute_command(
        self,
        command_type: AllowlistedCommandType,
        params: Dict[str, Any] = None,
    ) -> DesktopActionResult:
        """Executes an allowlisted system command without shell interpolation."""
        if command_type not in ALLOWED_SYSTEM_COMMANDS:
            raise ValueError(f"Command '{command_type}' is not recognized in system allowlist.")

        base_cmd = ALLOWED_SYSTEM_COMMANDS[command_type]

        if not self.is_windows:
            # Fallback for synthetic / cross-platform test environments
            return DesktopActionResult(
                action=DesktopActionType.RUN_ALLOWLISTED_COMMAND,
                status="success",
                message=f"Command '{command_type.value}' executed (simulated non-Windows environment).",
                data={"output": f"Simulated output for {command_type.value}"},
            )

        logger.info(f"Executing approved system command: {base_cmd}")
        try:
            result = subprocess.run(
                base_cmd,
                capture_output=True,
                text=True,
                timeout=15.0,
                shell=False,
            )

            success = result.returncode == 0
            output = result.stdout.strip() if success else result.stderr.strip()

            return DesktopActionResult(
                action=DesktopActionType.RUN_ALLOWLISTED_COMMAND,
                status="success" if success else "failed",
                message=f"Command '{command_type.value}' executed with return code {result.returncode}.",
                data={"output": output, "returncode": result.returncode},
            )
        except subprocess.TimeoutExpired:
            return DesktopActionResult(
                action=DesktopActionType.RUN_ALLOWLISTED_COMMAND,
                status="failed",
                message=f"Command '{command_type.value}' timed out after 15 seconds.",
            )
        except Exception as e:
            return DesktopActionResult(
                action=DesktopActionType.RUN_ALLOWLISTED_COMMAND,
                status="failed",
                message=f"Command '{command_type.value}' failed: {str(e)}",
            )


script_tools = ScriptTools()

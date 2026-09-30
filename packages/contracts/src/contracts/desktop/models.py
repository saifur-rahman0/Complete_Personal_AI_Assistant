from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class DesktopActionType(str, Enum):
    SYSTEM_TELEMETRY = "system_telemetry"
    APP_LAUNCH = "app_launch"
    APP_CLOSE = "app_close"
    LIST_WINDOWS = "list_windows"
    RUN_ALLOWLISTED_COMMAND = "run_allowlisted_command"


class AllowlistedCommandType(str, Enum):
    GET_IP_CONFIG = "get_ip_config"
    GET_WIFI_STATUS = "get_wifi_status"
    GET_DISK_SPACE = "get_disk_space"
    GET_SYSTEM_INFO = "get_system_info"
    FLUSH_DNS = "flush_dns"


class WindowInfo(BaseModel):
    title: str = Field(description="Visible window title")
    handle: Optional[int] = Field(default=None, description="Window handle (HWND)")
    process_name: Optional[str] = Field(default=None, description="Process executable name")


class SystemTelemetry(BaseModel):
    cpu_percent: float = Field(description="Current CPU utilization percentage (0.0 to 100.0)")
    memory_used_percent: float = Field(description="Physical memory utilization percentage (0.0 to 100.0)")
    memory_total_gb: float = Field(description="Total installed physical RAM in gigabytes")
    battery_percent: Optional[int] = Field(default=None, description="Battery charge percentage (0 to 100)")
    is_charging: Optional[bool] = Field(default=None, description="Whether AC power is connected")
    open_windows: List[WindowInfo] = Field(default_factory=list, description="Currently visible top-level windows")
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc), description="Timestamp of telemetry collection")


class AppLaunchRequest(BaseModel):
    app_name: str = Field(description="Allowlisted application identifier (e.g. notepad, calc, code)")
    arguments: List[str] = Field(default_factory=list, description="Safe arguments to pass to the application")


class AppCloseRequest(BaseModel):
    target: str = Field(description="Window title substring or process name to close")
    force: bool = Field(default=False, description="Whether to forcibly terminate the application process")


class AllowlistedScriptRequest(BaseModel):
    command: AllowlistedCommandType = Field(description="Approved system command to execute")
    params: Dict[str, Any] = Field(default_factory=dict, description="Validated parameters for the command")


class DesktopActionResult(BaseModel):
    action: DesktopActionType
    status: str = Field(description="'success' or 'failed'")
    message: str
    data: Optional[Dict[str, Any]] = None

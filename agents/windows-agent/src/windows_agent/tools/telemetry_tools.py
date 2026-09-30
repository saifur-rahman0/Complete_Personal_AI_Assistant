from datetime import datetime, timezone
import logging
import platform
import time
from typing import List, Optional

from contracts.desktop.models import SystemTelemetry, WindowInfo

logger = logging.getLogger("windows_agent.tools.telemetry")


class TelemetryTools:
    """
    Collects system metrics (CPU, RAM, Battery, Open Windows) directly using
    standard library native Windows APIs via ctypes, with safe fallbacks.
    """

    def __init__(self) -> None:
        self.is_windows = platform.system() == "Windows"
        self._last_idle_time = 0
        self._last_kernel_time = 0
        self._last_user_time = 0
        self._init_cpu_times()

    def _init_cpu_times(self) -> None:
        if not self.is_windows:
            return
        try:
            import ctypes
            from ctypes import wintypes

            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

            idle = FILETIME()
            kernel = FILETIME()
            user = FILETIME()
            if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle), ctypes.byref(kernel), ctypes.byref(user)):
                self._last_idle_time = (idle.dwHighDateTime << 32) + idle.dwLowDateTime
                self._last_kernel_time = (kernel.dwHighDateTime << 32) + kernel.dwLowDateTime
                self._last_user_time = (user.dwHighDateTime << 32) + user.dwLowDateTime
        except Exception as e:
            logger.debug(f"Failed to initialize CPU counters: {e}")

    def get_cpu_utilization(self) -> float:
        """Returns instantaneous CPU utilization percentage."""
        if not self.is_windows:
            return 15.0  # Synthetic fallback for mock/non-Windows environments

        try:
            import ctypes
            from ctypes import wintypes

            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", wintypes.DWORD), ("dwHighDateTime", wintypes.DWORD)]

            idle1, kernel1, user1 = FILETIME(), FILETIME(), FILETIME()
            ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1))

            time.sleep(0.05)  # brief sample window

            idle2, kernel2, user2 = FILETIME(), FILETIME(), FILETIME()
            ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2))

            to_int = lambda ft: (ft.dwHighDateTime << 32) + ft.dwLowDateTime
            d_idle = to_int(idle2) - to_int(idle1)
            d_kernel = to_int(kernel2) - to_int(kernel1)
            d_user = to_int(user2) - to_int(user1)
            total = d_kernel + d_user

            if total <= 0:
                return 0.0

            cpu = ((total - d_idle) / total) * 100.0
            return max(0.0, min(100.0, round(cpu, 1)))
        except Exception as e:
            logger.warning(f"Error reading CPU usage: {e}")
            return 0.0

    def get_memory_info(self) -> tuple[float, float]:
        """Returns (memory_used_percent, memory_total_gb)."""
        if not self.is_windows:
            return (45.0, 16.0)

        try:
            import ctypes
            from ctypes import wintypes

            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_ulonglong),
                    ("ullAvailPhys", ctypes.c_ulonglong),
                    ("ullTotalPageFile", ctypes.c_ulonglong),
                    ("ullAvailPageFile", ctypes.c_ulonglong),
                    ("ullTotalVirtual", ctypes.c_ulonglong),
                    ("ullAvailVirtual", ctypes.c_ulonglong),
                    ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
                ]

            mem = MEMORYSTATUSEX()
            mem.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)):
                used_pct = float(mem.dwMemoryLoad)
                total_gb = round(mem.ullTotalPhys / (1024**3), 2)
                return (used_pct, total_gb)
        except Exception as e:
            logger.warning(f"Error reading memory info: {e}")

        return (0.0, 0.0)

    def get_battery_info(self) -> tuple[Optional[int], Optional[bool]]:
        """Returns (battery_percent, is_charging)."""
        if not self.is_windows:
            return (80, True)

        try:
            import ctypes
            from ctypes import wintypes

            class SYSTEM_POWER_STATUS(ctypes.Structure):
                _fields_ = [
                    ("ACLineStatus", wintypes.BYTE),
                    ("BatteryFlag", wintypes.BYTE),
                    ("BatteryLifePercent", wintypes.BYTE),
                    ("SystemStatusFlag", wintypes.BYTE),
                    ("BatteryLifeTime", wintypes.DWORD),
                    ("BatteryFullLifeTime", wintypes.DWORD),
                ]

            sps = SYSTEM_POWER_STATUS()
            if ctypes.windll.kernel32.GetSystemPowerStatus(ctypes.byref(sps)):
                pct = None if sps.BatteryLifePercent == 255 else int(sps.BatteryLifePercent)
                charging = True if sps.ACLineStatus == 1 else False
                return (pct, charging)
        except Exception as e:
            logger.warning(f"Error reading battery status: {e}")

        return (None, None)

    def get_open_windows(self) -> List[WindowInfo]:
        """Enumerates visible top-level desktop windows."""
        windows: List[WindowInfo] = []
        if not self.is_windows:
            return [WindowInfo(title="Mock Desktop Window", handle=1001)]

        try:
            import ctypes
            from ctypes import wintypes

            def enum_proc(hwnd, lparam):
                if ctypes.windll.user32.IsWindowVisible(hwnd):
                    length = ctypes.windll.user32.GetWindowTextLengthW(hwnd)
                    if length > 0:
                        buff = ctypes.create_unicode_buffer(length + 1)
                        ctypes.windll.user32.GetWindowTextW(hwnd, buff, length + 1)
                        title = buff.value.strip()
                        # Filter out blank or invisible helper windows
                        if title and title not in ("Default IME", "MSCTFIME UI"):
                            windows.append(WindowInfo(title=title, handle=int(hwnd)))
                return True

            EnumProcType = ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
            ctypes.windll.user32.EnumWindows(EnumProcType(enum_proc), 0)
        except Exception as e:
            logger.warning(f"Error enumerating windows: {e}")

        return windows

    def collect_telemetry(self) -> SystemTelemetry:
        """Assembles full SystemTelemetry snapshot."""
        cpu = self.get_cpu_utilization()
        mem_pct, mem_total = self.get_memory_info()
        battery_pct, is_charging = self.get_battery_info()
        windows = self.get_open_windows()

        return SystemTelemetry(
            cpu_percent=cpu,
            memory_used_percent=mem_pct,
            memory_total_gb=mem_total,
            battery_percent=battery_pct,
            is_charging=is_charging,
            open_windows=windows,
            timestamp=datetime.now(timezone.utc),
        )


telemetry_tools = TelemetryTools()

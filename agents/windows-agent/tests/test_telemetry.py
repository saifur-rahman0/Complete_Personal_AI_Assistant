from contracts.desktop.models import SystemTelemetry
from windows_agent.tools.telemetry_tools import TelemetryTools


def test_collect_telemetry_returns_valid_structure():
    tools = TelemetryTools()
    telemetry = tools.collect_telemetry()

    assert isinstance(telemetry, SystemTelemetry)
    assert 0.0 <= telemetry.cpu_percent <= 100.0
    assert 0.0 <= telemetry.memory_used_percent <= 100.0
    assert telemetry.memory_total_gb >= 0.0
    assert isinstance(telemetry.open_windows, list)


def test_memory_info():
    tools = TelemetryTools()
    used_pct, total_gb = tools.get_memory_info()

    assert 0.0 <= used_pct <= 100.0
    assert total_gb > 0.0


def test_battery_info_types():
    tools = TelemetryTools()
    pct, is_charging = tools.get_battery_info()

    if pct is not None:
        assert 0 <= pct <= 100
    if is_charging is not None:
        assert isinstance(is_charging, bool)

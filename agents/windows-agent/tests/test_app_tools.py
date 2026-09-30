from unittest.mock import MagicMock, patch
import pytest
from contracts.desktop.models import DesktopActionType
from windows_agent.tools.app_tools import AppTools


def test_resolve_application_binary_approved():
    tools = AppTools()
    binary = tools.resolve_application_binary("notepad")
    assert "notepad" in binary.lower()

    binary_calc = tools.resolve_application_binary("calculator")
    assert "calc" in binary_calc.lower()


def test_resolve_application_binary_unapproved_raises():
    tools = AppTools()
    with pytest.raises(ValueError, match="not in the approved desktop allowlist"):
        tools.resolve_application_binary("malicious_app.exe")

    with pytest.raises(ValueError, match="not in the approved desktop allowlist"):
        tools.resolve_application_binary("powershell")


def test_launch_app_blocks_dangerous_arguments():
    tools = AppTools()
    with pytest.raises(ValueError, match="Dangerous character in application argument"):
        tools.launch_app("notepad", arguments=["file.txt; format c:"])

    with pytest.raises(ValueError, match="Dangerous character in application argument"):
        tools.launch_app("notepad", arguments=["file.txt & calc.exe"])


def test_launch_app_success_mocked():
    tools = AppTools()
    mock_proc = MagicMock()
    mock_proc.pid = 9999

    with patch("subprocess.Popen", return_value=mock_proc):
        result = tools.launch_app("notepad", arguments=["test.txt"])
        assert result.action == DesktopActionType.APP_LAUNCH
        assert result.status == "success"
        assert result.data["pid"] == 9999
        assert "launched successfully" in result.message


def test_close_app_unapproved_raises():
    tools = AppTools()
    with pytest.raises(ValueError, match="not an approved controllable app"):
        tools.close_app("critical_system_service")


def test_close_app_success_mocked():
    tools = AppTools()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "SUCCESS: The process has been terminated."
    mock_res.stderr = ""

    with patch("subprocess.run", return_value=mock_res):
        result = tools.close_app("notepad", force=True)
        assert result.action == DesktopActionType.APP_CLOSE
        assert result.status == "success"
        assert "closed successfully" in result.message

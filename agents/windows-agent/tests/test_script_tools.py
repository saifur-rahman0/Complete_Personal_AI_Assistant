from unittest.mock import MagicMock, patch
import pytest
from contracts.desktop.models import AllowlistedCommandType, DesktopActionType
from windows_agent.tools.script_tools import ScriptTools


def test_execute_allowlisted_command_ipconfig():
    tools = ScriptTools()
    mock_res = MagicMock()
    mock_res.returncode = 0
    mock_res.stdout = "Windows IP Configuration\nIPv4 Address: 192.168.1.50"
    mock_res.stderr = ""

    with patch("subprocess.run", return_value=mock_res):
        result = tools.execute_command(AllowlistedCommandType.GET_IP_CONFIG)
        assert result.action == DesktopActionType.RUN_ALLOWLISTED_COMMAND
        assert result.status == "success"
        assert "Windows IP Configuration" in result.data["output"]


def test_execute_allowlisted_command_timeout():
    import subprocess
    tools = ScriptTools()

    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd=["ipconfig"], timeout=15.0)):
        result = tools.execute_command(AllowlistedCommandType.GET_IP_CONFIG)
        assert result.status == "failed"
        assert "timed out" in result.message.lower()

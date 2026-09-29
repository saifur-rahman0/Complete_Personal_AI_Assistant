from pathlib import Path
import pytest
from windows_agent.safety import SecurityValidationError, is_safe_path, validate_path


def test_validate_path_inside_allowed_root(tmp_path):
    allowed_root = tmp_path.resolve()
    subfolder = allowed_root / "downloads"
    subfolder.mkdir()
    sample_file = subfolder / "notes.txt"
    sample_file.write_text("hello")

    # Valid subpath
    res = validate_path(sample_file, [allowed_root])
    assert res == sample_file.resolve()
    assert is_safe_path(sample_file, [allowed_root]) is True


def test_validate_path_traversal_blocked(tmp_path):
    allowed_root = tmp_path / "sandbox"
    allowed_root.mkdir()

    outside_file = tmp_path / "secret.txt"
    outside_file.write_text("secret")

    # Attempting to escape allowed_root via ..
    traversal_attempt = allowed_root / ".." / "secret.txt"

    with pytest.raises(SecurityValidationError):
        validate_path(traversal_attempt, [allowed_root])

    assert is_safe_path(traversal_attempt, [allowed_root]) is False


def test_validate_path_rejects_empty():
    with pytest.raises(SecurityValidationError):
        validate_path("", [Path.cwd()])


def test_validate_path_rejects_system_and_root_drives():
    with pytest.raises(SecurityValidationError):
        validate_path(r"C:\Windows\System32", [Path(r"C:\Windows")])

    with pytest.raises(SecurityValidationError):
        validate_path(r"C:\\", [Path(r"C:\\")])

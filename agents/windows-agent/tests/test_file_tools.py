from pathlib import Path
import pytest
from windows_agent.tools.file_tools import FileTools


@pytest.fixture
def sandbox_tools(tmp_path):
    # Isolated FileTools restricted only to tmp_path
    return FileTools(allowed_roots=[tmp_path.resolve()])


def test_list_and_search_directory(sandbox_tools, tmp_path):
    # Setup test files
    (tmp_path / "report.pdf").write_text("pdf content")
    (tmp_path / "photo.png").write_text("png content")
    sub = tmp_path / "subfolder"
    sub.mkdir()
    (sub / "nested.pdf").write_text("nested pdf")

    # List non-recursive
    items = sandbox_tools.list_directory(tmp_path, recursive=False)
    names = [i.name for i in items]
    assert "report.pdf" in names
    assert "photo.png" in names
    assert "subfolder" in names
    assert "nested.pdf" not in names

    # Search recursive
    pdf_results = sandbox_tools.search_files(tmp_path, pattern="*.pdf", recursive=True)
    pdf_names = [p.name for p in pdf_results]
    assert "report.pdf" in pdf_names
    assert "nested.pdf" in pdf_names
    assert "photo.png" not in pdf_names


def test_preview_and_execute_organize(sandbox_tools, tmp_path):
    # Setup unorganized files
    (tmp_path / "document1.pdf").write_text("content")
    (tmp_path / "document2.docx").write_text("content")
    (tmp_path / "photo1.png").write_text("content")
    (tmp_path / "archive.zip").write_text("content")

    # 1. Preview organize (Dry-run)
    preview = sandbox_tools.preview_organize(tmp_path, strategy="by_extension")
    assert preview["total_files"] == 4
    assert preview["categories"]["Documents"] == 2
    assert preview["categories"]["Images"] == 1
    assert preview["categories"]["Archives"] == 1

    # Files must still be at root (not moved yet)
    assert (tmp_path / "document1.pdf").exists()

    # 2. Execute organize
    result = sandbox_tools.execute_organize(tmp_path, strategy="by_extension")
    assert result.success is True
    assert result.affected_count == 4

    # Verify new folder structure
    assert (tmp_path / "Documents" / "document1.pdf").exists()
    assert (tmp_path / "Documents" / "document2.docx").exists()
    assert (tmp_path / "Images" / "photo1.png").exists()
    assert (tmp_path / "Archives" / "archive.zip").exists()
    assert not (tmp_path / "document1.pdf").exists()


def test_move_file(sandbox_tools, tmp_path):
    src = tmp_path / "source.txt"
    src.write_text("move me")
    dest_dir = tmp_path / "destination_folder"
    dest_dir.mkdir()

    res = sandbox_tools.move_file(src, dest_dir)
    assert res.success is True
    assert not src.exists()
    assert (dest_dir / "source.txt").exists()

import os
import shutil
import socket
import threading
import time
from pathlib import Path
import httpx
import pytest
import uvicorn

from contracts.approvals.models import ApprovalStatus
from contracts.router.models import IntentType
from contracts.tasks.models import TaskStatus, TaskTargetDevice
from decision_router.config import settings as router_settings
from decision_router.main import app as router_app
from task_service.main import app as task_app
from windows_agent.client import TaskServiceClient
from windows_agent.config import settings as agent_settings
from windows_agent.executor import TaskExecutor
from windows_agent.tools.file_tools import FileTools


def find_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_server(app, port: int) -> uvicorn.Server:
    config = uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)
    t = threading.Thread(target=server.run, daemon=True)
    t.start()

    # Wait for server to become responsive
    deadline = time.time() + 5.0
    while time.time() < deadline:
        try:
            with httpx.Client() as client:
                res = client.get(f"http://127.0.0.1:{port}/health")
                if res.status_code == 200:
                    return server
        except Exception:
            time.sleep(0.05)
    raise RuntimeError(f"Server on port {port} failed to start in time.")


@pytest.fixture(scope="module")
def e2e_cluster():
    """Spins up real task-service and decision-router instances on dynamic ports."""
    task_port = find_free_port()
    router_port = find_free_port()

    task_server = run_server(task_app, task_port)

    # Point router to the test task-service port
    router_settings.TASK_SERVICE_URL = f"http://127.0.0.1:{task_port}"
    router_server = run_server(router_app, router_port)

    yield {
        "task_service_url": f"http://127.0.0.1:{task_port}",
        "router_service_url": f"http://127.0.0.1:{router_port}",
    }

    task_server.should_exit = True
    router_server.should_exit = True


@pytest.fixture
def mock_downloads_folder(tmp_path):
    """Creates a temporary realistic Downloads folder with multi-category files."""
    downloads = tmp_path / "Downloads"
    downloads.mkdir(parents=True, exist_ok=True)

    test_files = [
        "invoice_2026.pdf",
        "meeting_notes.docx",
        "summary.txt",
        "screenshot_app.png",
        "camera_photo.jpg",
        "project_archive.zip",
        "script.py",
    ]

    for fname in test_files:
        (downloads / fname).write_text(f"Sample content for {fname}", encoding="utf-8")

    agent_settings.ALLOWED_ROOT_PATHS = f"{downloads.resolve()},{Path.cwd().resolve()}"
    return downloads


def test_e2e_file_slice_organize_approved(e2e_cluster, mock_downloads_folder):
    """
    Vertical Slice Test A: Full Loop with Human Approval
    1. Flutter client sends prompt to Decision Router /dispatch.
    2. Decision Router classifies as FILE_MANAGEMENT & creates Task in Task Service.
    3. Windows Agent claims task, prepares preview_organize, and requests approval.
    4. Task moves to awaiting_approval status.
    5. Flutter client fetches pending approvals and submits approval resolution (True).
    6. Windows Agent executes file moves, organizes files into subfolders, and marks task completed.
    7. Disk assertions verify categorized subfolders and moved files.
    """
    task_service_url = e2e_cluster["task_service_url"]
    router_service_url = e2e_cluster["router_service_url"]

    # 1. Dispatch prompt
    prompt = f'Organize folder "{mock_downloads_folder}"'
    with httpx.Client(timeout=10.0) as http_client:
        dispatch_res = http_client.post(
            f"{router_service_url}/api/v1/router/dispatch",
            json={"prompt": prompt, "device_context": "windows"},
        )
        assert dispatch_res.status_code == 200
        dispatch_data = dispatch_res.json()

        assert dispatch_data["decision"]["intent"] == IntentType.FILE_MANAGEMENT
        assert dispatch_data["decision"]["structured_action"] == "organize_folder"
        created_task = dispatch_data["task"]
        assert created_task is not None
        assert created_task["status"] == TaskStatus.PENDING
        task_id = created_task["id"]

    # 2. Configure Windows Agent worker/executor pointing to test environment
    client = TaskServiceClient(base_url=task_service_url)
    tools = FileTools()
    executor = TaskExecutor(client=client, tools=tools)

    # Allow operations in our tmp directory
    agent_settings.ALLOWED_ROOT_PATHS = f"{mock_downloads_folder.resolve()},{Path.cwd().resolve()}"

    # 3. Run worker execution in a background thread so the test can simulate the human user
    task = client.get_task(task_id)
    assert task is not None

    worker_thread = threading.Thread(target=executor.execute, args=(task,), daemon=True)
    worker_thread.start()

    # 4. Wait for approval request to appear in task-service (acting as Flutter client)
    time.sleep(0.5)
    pending_approvals = []
    with httpx.Client(timeout=10.0) as http_client:
        for _ in range(30):
            res = http_client.get(f"{task_service_url}/api/v1/approvals?status=pending")
            assert res.status_code == 200
            items = res.json()
            if items:
                pending_approvals = items
                break
            time.sleep(0.2)

    assert len(pending_approvals) >= 1
    approval = pending_approvals[0]
    assert approval["task_id"] == task_id
    assert approval["action_type"] == "folder_organize"
    assert approval["status"] == "pending"
    assert approval["details"]["total_files"] == 7

    # 5. User taps "Approve" in the Flutter Client
    with httpx.Client(timeout=10.0) as http_client:
        resolve_res = http_client.post(
            f"{task_service_url}/api/v1/approvals/{approval['id']}/resolve",
            json={"approved": True, "reason": "Approved by user via Flutter UI"},
        )
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == ApprovalStatus.APPROVED

    # 6. Wait for worker thread to finish executing disk operations
    worker_thread.join(timeout=10.0)
    assert not worker_thread.is_alive()

    # 7. Verify Task status is COMPLETED
    updated_task = client.get_task(task_id)
    assert updated_task.status == TaskStatus.COMPLETED
    assert "Organized 7 of 7 files" in updated_task.result_summary

    # 8. Verify Filesystem State on Disk
    assert (mock_downloads_folder / "Documents" / "invoice_2026.pdf").exists()
    assert (mock_downloads_folder / "Documents" / "meeting_notes.docx").exists()
    assert (mock_downloads_folder / "Documents" / "summary.txt").exists()
    assert (mock_downloads_folder / "Images" / "screenshot_app.png").exists()
    assert (mock_downloads_folder / "Images" / "camera_photo.jpg").exists()
    assert (mock_downloads_folder / "Archives" / "project_archive.zip").exists()
    assert (mock_downloads_folder / "Code" / "script.py").exists()


def test_e2e_file_slice_organize_rejected(e2e_cluster, mock_downloads_folder):
    """
    Vertical Slice Test B: Rejection Loop
    1. Prompt dispatched to organize folder.
    2. Windows Agent requests approval.
    3. User clicks "Reject" in Flutter client.
    4. Windows Agent halts; files remain completely untouched.
    5. Task status transitions to FAILED with rejection error.
    """
    task_service_url = e2e_cluster["task_service_url"]
    router_service_url = e2e_cluster["router_service_url"]

    # 1. Dispatch prompt
    prompt = f'Clean up folder "{mock_downloads_folder}"'
    with httpx.Client(timeout=10.0) as http_client:
        dispatch_res = http_client.post(
            f"{router_service_url}/api/v1/router/dispatch",
            json={"prompt": prompt, "device_context": "windows"},
        )
        assert dispatch_res.status_code == 200
        task_id = dispatch_res.json()["task"]["id"]

    client = TaskServiceClient(base_url=task_service_url)
    tools = FileTools()
    executor = TaskExecutor(client=client, tools=tools)

    agent_settings.ALLOWED_ROOT_PATHS = f"{mock_downloads_folder.resolve()},{Path.cwd().resolve()}"

    task = client.get_task(task_id)
    worker_thread = threading.Thread(target=executor.execute, args=(task,), daemon=True)
    worker_thread.start()

    # 2. Wait for approval request with polling
    time.sleep(0.5)
    approval = None
    with httpx.Client(timeout=10.0) as http_client:
        for _ in range(30):
            res = http_client.get(f"{task_service_url}/api/v1/approvals?status=pending")
            assert res.status_code == 200
            approvals = [a for a in res.json() if a["task_id"] == task_id]
            if approvals:
                approval = approvals[0]
                break
            time.sleep(0.2)

        assert approval is not None

        # 3. User clicks Reject
        resolve_res = http_client.post(
            f"{task_service_url}/api/v1/approvals/{approval['id']}/resolve",
            json={"approved": False, "reason": "Not ready to organize right now"},
        )
        assert resolve_res.status_code == 200
        assert resolve_res.json()["status"] == ApprovalStatus.REJECTED

    worker_thread.join(timeout=10.0)
    assert not worker_thread.is_alive()

    # 4. Verify Task is marked failed / rejected
    updated_task = client.get_task(task_id)
    assert updated_task.status == TaskStatus.FAILED
    assert "rejected" in updated_task.error_message.lower()

    # 5. Verify Disk was NOT touched (all 7 files still in root folder)
    assert (mock_downloads_folder / "invoice_2026.pdf").exists()
    assert (mock_downloads_folder / "meeting_notes.docx").exists()
    assert not (mock_downloads_folder / "Documents").exists()


def test_e2e_file_slice_search_files(e2e_cluster, mock_downloads_folder):
    """
    Vertical Slice Test C: Read-Only Tool Path (No approval prompt needed)
    1. User asks to find all PDF files in folder.
    2. Decision Router extracts pattern *.pdf.
    3. Windows Agent executes search_files immediately without halting for approval.
    4. Task marked COMPLETED with search results.
    """
    task_service_url = e2e_cluster["task_service_url"]
    router_service_url = e2e_cluster["router_service_url"]

    prompt = f'Find all pdf files in "{mock_downloads_folder}"'
    with httpx.Client(timeout=10.0) as http_client:
        dispatch_res = http_client.post(
            f"{router_service_url}/api/v1/router/dispatch",
            json={"prompt": prompt, "device_context": "windows"},
        )
        assert dispatch_res.status_code == 200
        task_id = dispatch_res.json()["task"]["id"]

    client = TaskServiceClient(base_url=task_service_url)
    tools = FileTools()
    executor = TaskExecutor(client=client, tools=tools)

    agent_settings.ALLOWED_ROOT_PATHS = f"{mock_downloads_folder.resolve()},{Path.cwd().resolve()}"

    task = client.get_task(task_id)
    executor.execute(task)

    updated_task = client.get_task(task_id)
    assert updated_task.status == TaskStatus.COMPLETED
    assert "Found 1 files" in updated_task.result_summary

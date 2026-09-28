import pytest
from fastapi.testclient import TestClient
from task_service.main import create_app
from contracts.tasks.models import TaskPriority, TaskStatus, TaskTargetDevice


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health_endpoints(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ok"


def test_task_crud_lifecycle(client):
    # 1. Create Task
    create_payload = {
        "title": "Clean Downloads folder",
        "description": "Organize PDF and image files into subfolders",
        "target_device": "windows",
        "priority": "normal",
        "payload": {"folder": "C:/Users/User/Downloads"},
    }
    create_res = client.post("/api/v1/tasks", json=create_payload)
    assert create_res.status_code == 201
    task_data = create_res.json()
    task_id = task_data["id"]
    assert task_data["title"] == "Clean Downloads folder"
    assert task_data["status"] == "pending"

    # 2. Get Task
    get_res = client.get(f"/api/v1/tasks/{task_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == task_id

    # 3. List Tasks
    list_res = client.get("/api/v1/tasks")
    assert list_res.status_code == 200
    assert list_res.json()["total"] >= 1
    assert any(t["id"] == task_id for t in list_res.json()["items"])

    # 4. Update Task Status
    update_res = client.patch(
        f"/api/v1/tasks/{task_id}",
        json={"status": "running"},
    )
    assert update_res.status_code == 200
    assert update_res.json()["status"] == "running"


def test_approval_lifecycle(client):
    # 1. Create a task first
    task_res = client.post(
        "/api/v1/tasks",
        json={"title": "Delete temporary log files", "target_device": "windows"},
    )
    task_id = task_res.json()["id"]

    # 2. Request human approval (e.g. for destructive file deletion)
    approval_res = client.post(
        "/api/v1/approvals",
        json={
            "task_id": task_id,
            "action_type": "file_delete",
            "description": "Delete 15 outdated log files totaling 1.2 GB",
            "details": {"files": ["log1.txt", "log2.txt"]},
        },
    )
    assert approval_res.status_code == 201
    approval_id = approval_res.json()["id"]
    assert approval_res.json()["status"] == "pending"

    # Task should now be in AWAITING_APPROVAL status
    task_check = client.get(f"/api/v1/tasks/{task_id}").json()
    assert task_check["status"] == "awaiting_approval"

    # 3. List pending approvals (as Android companion would)
    pending_list = client.get("/api/v1/approvals?status=pending").json()
    assert any(a["id"] == approval_id for a in pending_list)

    # 4. Resolve approval (Approve)
    resolve_res = client.post(
        f"/api/v1/approvals/{approval_id}/resolve",
        json={"approved": True, "reason": "Looks good, proceed with cleanup"},
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "approved"

    # Task status resumes
    task_final = client.get(f"/api/v1/tasks/{task_id}").json()
    assert task_final["status"] == "running"

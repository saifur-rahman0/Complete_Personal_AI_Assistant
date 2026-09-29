import time
from fastapi.testclient import TestClient
import pytest
from contracts.router.models import IntentType, RouteRequest
from decision_router.classifiers.system_one import system_one_classifier
from decision_router.main import create_app


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_health_endpoints(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.json()["service"] == "decision-router"

    res_ready = client.get("/ready")
    assert res_ready.status_code == 200
    assert res_ready.json()["status"] == "ok"


def test_system_one_sub_50ms_latency():
    req = RouteRequest(prompt="Organize my downloads folder")
    start = time.perf_counter()
    decision = system_one_classifier.classify(req)
    duration_ms = (time.perf_counter() - start) * 1000

    # Must be sub-50ms (System One standard)
    assert duration_ms < 50.0
    assert decision.intent == IntentType.FILE_MANAGEMENT
    assert decision.structured_action == "organize_folder"


def test_classify_file_organize(client):
    res = client.post("/api/v1/router/classify", json={"prompt": "Please organize my downloads folder"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "file_management"
    assert data["structured_action"] == "organize_folder"
    assert "downloads" in data["structured_payload"]["directory_path"].lower()


def test_classify_file_search(client):
    res = client.post("/api/v1/router/classify", json={"prompt": "Find all pdf files in documents"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "file_management"
    assert data["structured_action"] == "search_files"
    assert data["structured_payload"]["pattern"] == "*.pdf"
    assert "documents" in data["structured_payload"]["directory_path"].lower()


def test_classify_file_move(client):
    res = client.post("/api/v1/router/classify", json={"prompt": "Move report.pdf from downloads to documents"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "file_management"
    assert data["structured_action"] == "move_file"


def test_classify_reminder(client):
    res = client.post("/api/v1/router/classify", json={"prompt": "Remind me to take medication at 8 PM"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "reminder"
    assert data["target_service"] == "automation-service"


def test_classify_web_research(client):
    res = client.post("/api/v1/router/classify", json={"prompt": "Search the web for latest quantum computing breakthroughs"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "web_research"
    assert data["target_service"] == "web-research"


def test_classify_general_chat(client):
    res = client.post("/api/v1/router/classify", json={"prompt": "What is the capital of France?"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "general_query"
    assert data["requires_deep_reasoning"] is True

import time
from fastapi.testclient import TestClient
import pytest
from contracts.router.models import IntentType, RouteRequest
from decision_router.classifiers.system_one import system_one_classifier
from decision_router.main import create_app


from decision_router.config import settings


@pytest.fixture(autouse=True)
def disable_neural_for_router_tests(monkeypatch):
    """Ensures test_router.py tests run fast offline heuristics."""
    monkeypatch.setattr(settings, "USE_NEURAL_LAYA", False)


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


def test_dispatch_conversational_greeting(client):
    res = client.post("/api/v1/router/dispatch", json={"prompt": "hi"})
    assert res.status_code == 200
    data = res.json()
    assert data["decision"]["intent"] == "general_query"
    assert "Hello! I am Jarvis" in data["message"]


def test_dispatch_web_research(client):
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "mock-report-id",
        "query": "latest quantum computing breakthroughs",
        "summary": "Quantum computing is advancing with new topological qubits.",
        "key_findings": ["Topological qubits show high stability."],
        "sources": [],
        "created_at": "2026-09-29T12:00:00Z",
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_resp
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.__exit__.return_value = None

    with patch("decision_router.api.routes.route.httpx.Client", return_value=mock_client_instance):
        res = client.post(
            "/api/v1/router/dispatch",
            json={"prompt": "Search the web for latest quantum computing breakthroughs"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["decision"]["intent"] == "web_research"
        assert "Quantum computing is advancing" in data["message"]


def test_classify_desktop_telemetry(client):
    res = client.post("/api/v1/router/classify", json={"prompt": "Check my system status and battery level"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "desktop_automation"
    assert data["target_service"] == "windows-agent"
    assert data["structured_action"] == "system_telemetry"


def test_classify_desktop_app_launch(client):
    res = client.post("/api/v1/router/classify", json={"prompt": "Please open notepad"})
    assert res.status_code == 200
    data = res.json()
    assert data["intent"] == "desktop_automation"
    assert data["target_service"] == "windows-agent"
    assert data["structured_action"] == "app_launch"
    assert data["structured_payload"]["app_name"] == "notepad"


def test_dispatch_desktop_automation(client):
    from unittest.mock import MagicMock, patch

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "id": "mock-desktop-task-id",
        "title": "Desktop Action: System Telemetry",
        "description": "Check my system status",
        "target_device": "windows",
        "priority": "normal",
        "status": "pending",
        "payload": {"action": "system_telemetry"},
        "created_at": "2026-09-29T12:00:00Z",
        "updated_at": "2026-09-29T12:00:00Z",
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.post.return_value = mock_resp
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.__exit__.return_value = None

    with patch("decision_router.api.routes.route.httpx.Client", return_value=mock_client_instance):
        res = client.post(
            "/api/v1/router/dispatch",
            json={"prompt": "Check my system status"},
        )
        assert res.status_code == 200
        data = res.json()
        assert data["decision"]["intent"] == "desktop_automation"
        assert "Dispatched desktop task" in data["message"]
        assert data["task"]["id"] == "mock-desktop-task-id"


def test_llm_extractor_gemini_online():
    from unittest.mock import MagicMock, patch
    from decision_router.classifiers.llm_extractor import llm_extractor
    from decision_router.config import settings

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "content": {
                    "parts": [{"text": "Hello! I am Jarvis running on Google Gemini."}]
                }
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    with patch.object(settings, "GEMINI_API_KEY", "test-gemini-key"):
        with patch("decision_router.classifiers.llm_extractor.httpx.Client", return_value=mock_client):
            reply = llm_extractor.generate_chat_response("hi")
            assert reply == "Hello! I am Jarvis running on Google Gemini."


def test_llm_extractor_groq_online():
    from unittest.mock import MagicMock, patch
    from decision_router.classifiers.llm_extractor import llm_extractor
    from decision_router.config import settings

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "choices": [
            {
                "message": {"content": "Hello! Ultra-fast response from Groq Llama 3.3."}
            }
        ]
    }
    mock_resp.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.post.return_value = mock_resp
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None

    with patch.object(settings, "GEMINI_API_KEY", None):
        with patch.object(settings, "GROQ_API_KEY", "test-groq-key"):
            with patch("decision_router.classifiers.llm_extractor.httpx.Client", return_value=mock_client):
                reply = llm_extractor.generate_chat_response("hello")
                assert reply == "Hello! Ultra-fast response from Groq Llama 3.3."





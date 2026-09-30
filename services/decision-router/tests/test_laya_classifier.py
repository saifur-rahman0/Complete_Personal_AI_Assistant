from unittest.mock import MagicMock, patch
import pytest
from contracts.router.models import IntentType, RouteRequest
from decision_router.classifiers.laya_classifier import NeuralLayaClassifier, neural_laya_classifier
from decision_router.main import create_app
from fastapi.testclient import TestClient


@pytest.fixture
def client():
    app = create_app()
    return TestClient(app)


def test_laya_availability():
    classifier = NeuralLayaClassifier()
    # In this environment, laya is installed in .venv
    assert classifier.is_available() is True


def test_laya_fallback_on_uninstalled():
    with patch("builtins.__import__", side_effect=ImportError("No module named laya")):
        classifier = NeuralLayaClassifier()
        classifier._is_loaded = False
        classifier._agent = None
        # Should gracefully fall back to heuristic System One
        req = RouteRequest(prompt="Organize my downloads folder")
        decision = classifier.classify(req)
        assert decision.intent == IntentType.FILE_MANAGEMENT
        assert decision.structured_action == "organize_folder"


def test_laya_file_management_routing():
    classifier = NeuralLayaClassifier()
    classifier._is_loaded = True
    classifier._agent = MagicMock()

    mock_res = {
        "intent": {
            "choice": "file_management",
            "confidence": 0.94,
        }
    }

    with patch("laya.decide", return_value=mock_res):
        req = RouteRequest(prompt="Please organize my downloads folder")
        decision = classifier.classify(req)
        assert decision.intent == IntentType.FILE_MANAGEMENT
        assert decision.target_service == "windows-agent"
        assert decision.structured_action == "organize_folder"
        assert decision.confidence >= 0.85


def test_laya_reminder_routing():
    classifier = NeuralLayaClassifier()
    classifier._is_loaded = True
    classifier._agent = MagicMock()

    mock_res = {
        "intent": {
            "choice": "reminder",
            "confidence": 0.96,
        }
    }

    with patch("laya.decide", return_value=mock_res):
        req = RouteRequest(prompt="Remind me in 15 minutes to call Sarah")
        decision = classifier.classify(req)
        assert decision.intent == IntentType.REMINDER
        assert decision.target_service == "automation-service"
        assert decision.structured_action == "create_reminder"
        assert "sarah" in decision.structured_payload["title"].lower()


def test_laya_desktop_automation_routing():
    classifier = NeuralLayaClassifier()
    classifier._is_loaded = True
    classifier._agent = MagicMock()

    mock_res = {
        "intent": {
            "choice": "desktop_automation",
            "confidence": 0.92,
        }
    }

    with patch("laya.decide", return_value=mock_res):
        req = RouteRequest(prompt="Check battery and CPU usage")
        decision = classifier.classify(req)
        assert decision.intent == IntentType.DESKTOP_AUTOMATION
        assert decision.target_service == "windows-agent"
        assert decision.structured_action == "system_telemetry"


def test_laya_web_research_routing():
    classifier = NeuralLayaClassifier()
    classifier._is_loaded = True
    classifier._agent = MagicMock()

    mock_res = {
        "intent": {
            "choice": "web_research",
            "confidence": 0.89,
        }
    }

    with patch("laya.decide", return_value=mock_res):
        req = RouteRequest(prompt="Search online for quantum algorithms")
        decision = classifier.classify(req)
        assert decision.intent == IntentType.WEB_RESEARCH
        assert decision.target_service == "web-research"
        assert decision.structured_payload["query"] == "Search online for quantum algorithms"


def test_classify_endpoint_use_neural(client):
    mock_res = {
        "intent": {
            "choice": "file_management",
            "confidence": 0.95,
        }
    }

    with patch.object(neural_laya_classifier, "_is_loaded", True), \
         patch.object(neural_laya_classifier, "_agent", MagicMock()), \
         patch("laya.decide", return_value=mock_res):
        res = client.post(
            "/api/v1/router/classify?use_neural=true",
            json={"prompt": "Organize downloads folder"}
        )
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "file_management"
        assert data["target_service"] == "windows-agent"

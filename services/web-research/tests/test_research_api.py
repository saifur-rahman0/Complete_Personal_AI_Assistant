from unittest.mock import MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from contracts.research.models import WebSourceResult
from web_research.main import app


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["service"] == "web-research"
    assert data["port"] == 8004


def test_extract_url_ssrf_blocked(client):
    # SSRF URLs should be safely caught and return blocked status without error
    forbidden_url = "http://169.254.169.254/latest/meta-data/"
    response = client.post("/api/v1/research/extract", json={"url": forbidden_url})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "blocked_ssrf"
    assert "blocked by ssrf policy" in data["error_message"].lower()


def test_extract_url_safe_mocked(client, monkeypatch):
    mock_result = WebSourceResult(
        url="https://en.wikipedia.org/wiki/Artificial_intelligence",
        title="Artificial Intelligence",
        content_markdown="# Artificial Intelligence\n\nAI is intelligence demonstrated by machines.",
        snippet="AI is intelligence demonstrated by machines.",
        status="success",
    )

    with patch("web_research.api.routes.research.safe_crawler.fetch_page", return_value=mock_result):
        response = client.post(
            "/api/v1/research/extract",
            json={"url": "https://en.wikipedia.org/wiki/Artificial_intelligence"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["title"] == "Artificial Intelligence"
        assert data["status"] == "success"
        assert "intelligence demonstrated by machines" in data["content_markdown"]


def test_perform_research_search_and_get_report(client):
    mock_sources = [
        WebSourceResult(
            url="https://docs.python.org/3/",
            title="Python Documentation",
            content_markdown="# Python 3 Documentation\n\nOfficial documentation for Python.",
            snippet="Official documentation for Python.",
            status="success",
        ),
        WebSourceResult(
            url="https://en.wikipedia.org/wiki/Python_(programming_language)",
            title="Python Language",
            content_markdown="# Python\n\nPython is a high-level programming language.",
            snippet="Python is a high-level programming language.",
            status="success",
        ),
    ]

    with patch("web_research.api.routes.research.safe_crawler.search_and_crawl", return_value=mock_sources):
        # 1. Trigger research search
        search_res = client.post(
            "/api/v1/research/search",
            json={"query": "Python Programming", "max_sources": 2},
        )
        assert search_res.status_code == 200
        report = search_res.json()
        assert report["query"] == "Python Programming"
        assert len(report["sources"]) == 2
        assert len(report["key_findings"]) >= 1
        assert "Python" in report["summary"]
        report_id = report["id"]

        # 2. Retrieve report by ID from cache
        get_res = client.get(f"/api/v1/research/reports/{report_id}")
        assert get_res.status_code == 200
        cached_report = get_res.json()
        assert cached_report["id"] == report_id
        assert cached_report["query"] == "Python Programming"


def test_get_nonexistent_report_returns_404(client):
    response = client.get("/api/v1/research/reports/non-existent-uuid-1234")
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()

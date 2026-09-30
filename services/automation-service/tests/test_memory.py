from fastapi.testclient import TestClient
import pytest
from contracts.memory.models import MemoryCategory
from automation_service.main import app
from automation_service.repository.in_memory import memory_repo


@pytest.fixture(autouse=True)
def clean_memory():
    memory_repo._entries.clear()
    memory_repo._vectors.clear()
    yield
    memory_repo._entries.clear()
    memory_repo._vectors.clear()


@pytest.fixture
def client():
    return TestClient(app)


def test_store_and_get_memory(client):
    payload = {
        "content": "User prefers dark mode for all desktop applications",
        "category": "preference",
        "metadata": {"theme": "dark"},
    }

    res = client.post("/api/v1/memory", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["content"] == payload["content"]
    assert data["category"] == MemoryCategory.PREFERENCE
    entry_id = data["id"]

    get_res = client.get(f"/api/v1/memory/{entry_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == entry_id


def test_semantic_search_and_fallback(client):
    client.post(
        "/api/v1/memory",
        json={"content": "Primary work laptop is a Lenovo ThinkPad Windows 11", "category": "fact"},
    )
    client.post(
        "/api/v1/memory",
        json={"content": "Always organize downloads by grouping files by extension", "category": "preference"},
    )
    client.post(
        "/api/v1/memory",
        json={"content": "Family dog name is Milo", "category": "fact"},
    )

    # Search for laptop query
    search_res = client.post(
        "/api/v1/memory/search",
        json={"query": "What laptop does the user use?", "min_similarity": 0.1},
    )
    assert search_res.status_code == 200
    results = search_res.json()["results"]
    assert len(results) >= 1
    assert "ThinkPad" in results[0]["content"]


def test_filter_by_category(client):
    client.post("/api/v1/memory", json={"content": "Note 1", "category": "note"})
    client.post("/api/v1/memory", json={"content": "Pref 1", "category": "preference"})

    res = client.get("/api/v1/memory?category=preference")
    assert res.status_code == 200
    items = res.json()
    assert len(items) == 1
    assert items[0]["content"] == "Pref 1"

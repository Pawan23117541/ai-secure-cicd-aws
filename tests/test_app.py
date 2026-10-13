import pytest

from app.main import TASKS, app


@pytest.fixture
def client():
    TASKS.clear()
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def test_home(client):
    res = client.get("/")
    assert res.status_code == 200
    assert "Hello" in res.get_json()["message"]


def test_health(client):
    res = client.get("/health")
    assert res.status_code == 200
    assert res.get_json()["status"] == "ok"


def test_add_and_list_tasks(client):
    res = client.post("/api/tasks", json={"title": "Learn Bedrock"})
    assert res.status_code == 201
    assert res.get_json()["title"] == "Learn Bedrock"

    res = client.get("/api/tasks")
    assert len(res.get_json()["tasks"]) == 1


def test_add_task_requires_title(client):
    res = client.post("/api/tasks", json={})
    assert res.status_code == 400


def test_add_task_rejects_long_title(client):
    res = client.post("/api/tasks", json={"title": "x" * 201})
    assert res.status_code == 400


def test_unknown_route_returns_404(client):
    res = client.get("/does-not-exist")
    assert res.status_code == 404

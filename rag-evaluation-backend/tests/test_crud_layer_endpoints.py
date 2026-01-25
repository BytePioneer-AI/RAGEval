from datetime import datetime
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app.api import deps
from app.main import app
from app.schemas.question import QuestionBatchImport


class DummyUser:
    def __init__(self, user_id: str, is_admin: bool = False) -> None:
        self.id = user_id
        self.is_admin = is_admin
        self.is_active = True


@pytest.fixture
def client():
    def override_get_db():
        class DummyDB:
            def __getattr__(self, name):
                raise AssertionError("endpoint should not use db directly")

        yield DummyDB()

    app.dependency_overrides[deps.get_db] = override_get_db
    app.dependency_overrides[deps.get_current_user] = lambda: DummyUser("user-1")
    app.dependency_overrides[deps.get_current_active_admin] = lambda: DummyUser(
        "admin-1",
        is_admin=True,
    )

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides = {}


def test_admin_statistics_uses_service(client, monkeypatch):
    from app.api.api_v1.endpoints import admin as admin_endpoint

    expected = {
        "users": {"total": 10, "active": 8, "admin": 1},
        "projects": {"total": 2},
        "datasets": {"total": 3, "public": 1},
        "questions": {"total": 5},
    }

    monkeypatch.setattr(
        admin_endpoint,
        "get_system_statistics_service",
        lambda db: expected,
    )

    response = client.get("/api/v1/admin/statistics")
    assert response.status_code == 200
    assert response.json() == expected


def test_datasets_list_uses_service(client, monkeypatch):
    from app.api.api_v1.endpoints import datasets as datasets_endpoint

    now = datetime.utcnow().isoformat()
    item = {
        "id": "dataset-1",
        "user_id": "user-1",
        "name": "Dataset",
        "description": None,
        "is_public": False,
        "tags": [],
        "dataset_metadata": {},
        "question_count": 0,
        "created_at": now,
        "updated_at": now,
    }

    monkeypatch.setattr(
        datasets_endpoint,
        "list_datasets_page",
        lambda db, **kwargs: {"items": [item], "total": 1},
    )

    response = client.get("/api/v1/datasets")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == "dataset-1"


def test_projects_list_uses_service(client, monkeypatch):
    from app.api.api_v1.endpoints import projects as projects_endpoint

    now = datetime.utcnow()
    project = SimpleNamespace(
        id="project-1",
        user_id="user-1",
        name="Project",
        description=None,
        status="created",
        scoring_scale="1-5",
        evaluation_dimensions=[],
        created_at=now,
        updated_at=now,
    )

    monkeypatch.setattr(projects_endpoint, "get_projects_by_user", lambda db, **kw: [project])
    monkeypatch.setattr(projects_endpoint, "count_projects_by_user", lambda db, **kw: 1)

    response = client.get("/api/v1/projects")
    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["id"] == "project-1"


def test_questions_create_uses_services(client, monkeypatch):
    from app.api.api_v1.endpoints import questions as questions_endpoint

    now = datetime.utcnow()
    project = SimpleNamespace(id="project-1", user_id="user-1")
    question = SimpleNamespace(
        id="question-1",
        dataset_id="dataset-1",
        question_text="Q?",
        standard_answer="A",
        category=None,
        difficulty=None,
        type="text",
        tags={},
        question_metadata={},
        created_at=now,
        updated_at=now,
        rag_answers=[],
    )

    monkeypatch.setattr(questions_endpoint, "get_project", lambda db, project_id: project)
    monkeypatch.setattr(questions_endpoint, "create_question", lambda db, obj_in: question)

    response = client.post(
        "/api/v1/questions",
        json={
            "dataset_id": "dataset-1",
            "question_text": "Q?",
            "standard_answer": "A",
        },
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "question-1"


def test_import_questions_uses_services(monkeypatch):
    from app.api.api_v1.endpoints import import_export as import_export_endpoint

    dataset = SimpleNamespace(id="dataset-1", user_id="user-1", is_public=False)
    imported = [SimpleNamespace(id="q1"), SimpleNamespace(id="q2")]

    monkeypatch.setattr(import_export_endpoint, "get_dataset", lambda db, dataset_id: dataset)
    monkeypatch.setattr(
        import_export_endpoint,
        "import_questions_with_rag_answers",
        lambda db, dataset_id, questions: imported,
    )

    result = import_export_endpoint.import_questions_with_rag_answers_api(
        db=object(),
        import_data=QuestionBatchImport(dataset_id="dataset-1", questions=[]),
        current_user=DummyUser("user-1"),
    )

    assert result["success"] is True
    assert result["imported_count"] == 2

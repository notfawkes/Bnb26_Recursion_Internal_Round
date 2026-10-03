import pytest
import os
from fastapi.testclient import TestClient
from app.main import app
from app.storage.database import Database
from app.dependencies import get_db, mock_builder_manager


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    os.environ["APP_ENV"] = "testing"
    yield


@pytest.fixture
def test_db(tmp_path):
    db_file = tmp_path / "test_quorum.db"
    db_instance = Database(db_path=str(db_file))
    yield db_instance


@pytest.fixture
def client(test_db):
    def _get_test_db():
        return test_db

    app.dependency_overrides[get_db] = _get_test_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()

import pytest
import os
from fastapi.testclient import TestClient
from app.main import app


@pytest.fixture(scope="session", autouse=True)
def setup_test_env():
    os.environ["APP_ENV"] = "testing"
    yield


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


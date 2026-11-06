import os
import tempfile
from pathlib import Path

import pytest

TEST_ROOT = Path(tempfile.mkdtemp(prefix="ayna-tests-"))
os.environ["ENVIRONMENT"] = "test"
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_ROOT / 'test.db').as_posix()}"
os.environ["QUEUE_MODE"] = "inline"
os.environ["STORAGE_BACKEND"] = "local"
os.environ["LOCAL_STORAGE_PATH"] = str(TEST_ROOT / "assets")
os.environ["AI_PROVIDER"] = "mock"
os.environ["DEV_AUTH_ENABLED"] = "true"

from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture(autouse=True)
def database():
    config = Config("alembic.ini")
    command.upgrade(config, "head")
    yield
    command.downgrade(config, "base")


@pytest.fixture
def client():
    with TestClient(app) as instance:
        yield instance


@pytest.fixture
def owner():
    return {"X-Dev-Seller-Id": "11111111-1111-4111-8111-111111111111"}

import os
import sys
from uuid import uuid4
from io import BytesIO
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[2]
TEST_ROOT = PROJECT_DIR / ".task-temp"
TEST_ROOT.mkdir(exist_ok=True)
TEST_DIR = TEST_ROOT / f"api-tests-{uuid4().hex}"
TEST_DIR.mkdir()
os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["UPLOAD_DIR"] = str(TEST_DIR / "uploads")
sys.path.insert(0, str(PROJECT_DIR / "backend"))

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app.config import settings
from app.database import Base, engine
from app.main import app


@pytest.fixture(autouse=True)
def clean_database():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    settings.upload_dir.mkdir(parents=True, exist_ok=True)
    yield
    Base.metadata.drop_all(bind=engine)
    for path in settings.upload_dir.glob("*"):
        if path.is_file() and path.name != ".gitkeep":
            path.unlink()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def image_bytes() -> bytes:
    output = BytesIO()
    Image.new("RGB", (32, 32), color=(235, 132, 42)).save(output, format="JPEG")
    return output.getvalue()


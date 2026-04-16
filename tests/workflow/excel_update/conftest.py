from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import src.db.session as db_session
from src.api.app import app
from src.config.settings import settings
from src.db.session import init_db


@pytest.fixture()
def excel_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[Path]:
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{tmp_path / 'excel-update.db'}")
    monkeypatch.setattr(settings, "excel_update_output_dir", str(tmp_path / "excel-output"))
    db_session.engine = None
    db_session.SessionLocal.configure(bind=None)
    init_db()
    yield tmp_path
    db_session.engine = None
    db_session.SessionLocal.configure(bind=None)


@pytest.fixture()
def client(excel_env: Path) -> Iterator[TestClient]:
    with TestClient(app) as test_client:
        yield test_client

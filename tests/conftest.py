from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app
from backend.services.state import state_store


@pytest.fixture(autouse=True)
def isolate_state(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    pref = tmp_path / "user_preferences.json"
    conn = tmp_path / "connections.json"
    pref.write_text('{"preferences": {}}', encoding="utf-8")
    conn.write_text('{"connections": {}}', encoding="utf-8")

    monkeypatch.setattr(state_store, "preferences_file", pref)
    monkeypatch.setattr(state_store, "connections_file", conn)


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)

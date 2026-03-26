import json
from pathlib import Path
from typing import Dict, Optional

from backend.api.models import ServiceConnection, UserServicePreference
from backend.config import DATA_DIR
from backend.utils.logger import get_logger

logger = get_logger()


class StateStore:
    def __init__(self) -> None:
        self.preferences_file = DATA_DIR / "user_preferences.json"
        self.connections_file = DATA_DIR / "connections.json"

    def _read_json(self, path: Path, fallback: Dict) -> Dict:
        if not path.exists():
            return fallback
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.exception("Invalid JSON in state file: %s", path)
            return fallback

    def _write_json(self, path: Path, payload: Dict) -> None:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def save_preference(self, pref: UserServicePreference) -> UserServicePreference:
        payload = self._read_json(self.preferences_file, {"preferences": {}})
        payload["preferences"][pref.user_id] = pref.model_dump()
        self._write_json(self.preferences_file, payload)
        return pref

    def get_preference(self, user_id: str) -> Optional[UserServicePreference]:
        payload = self._read_json(self.preferences_file, {"preferences": {}})
        raw = payload.get("preferences", {}).get(user_id)
        if not raw:
            return None
        return UserServicePreference(**raw)

    def save_connection(self, conn: ServiceConnection) -> ServiceConnection:
        payload = self._read_json(self.connections_file, {"connections": {}})
        payload["connections"][conn.user_id] = conn.model_dump()
        self._write_json(self.connections_file, payload)
        return conn

    def get_connection(self, user_id: str) -> Optional[ServiceConnection]:
        payload = self._read_json(self.connections_file, {"connections": {}})
        raw = payload.get("connections", {}).get(user_id)
        if not raw:
            return None
        return ServiceConnection(**raw)

    def increment_request_count(self, user_id: str) -> Optional[ServiceConnection]:
        conn = self.get_connection(user_id)
        if not conn:
            return None
        conn.requests_count += 1
        self.save_connection(conn)
        return conn


state_store = StateStore()

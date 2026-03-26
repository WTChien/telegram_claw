import json
import os
from pathlib import Path
from typing import Any, Dict

from dotenv import load_dotenv

load_dotenv()

ROOT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT_DIR / "data"
CONFIG_DIR = ROOT_DIR / "config"
LOGS_DIR = ROOT_DIR / "logs"


class Settings:
    api_host: str = os.getenv("API_HOST", "0.0.0.0")
    api_port: int = int(os.getenv("API_PORT", "8000"))

    known_services_json: str = os.getenv(
        "KNOWN_SERVICES_JSON", str(CONFIG_DIR / "services.json")
    )
    port_scan_timeout: float = float(os.getenv("PORT_SCAN_TIMEOUT", "0.5"))
    port_scan_threads: int = int(os.getenv("PORT_SCAN_THREADS", "10"))

    log_level: str = os.getenv("LOG_LEVEL", "INFO")
    log_file: str = os.getenv("LOG_FILE", str(LOGS_DIR / "nanoclaw.log"))

    telegram_bot_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    admin_user_id: str = os.getenv("ADMIN_USER_ID", "")


settings = Settings()


def ensure_runtime_files() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    defaults: Dict[Path, Dict[str, Any]] = {
        DATA_DIR / "user_preferences.json": {"preferences": {}},
        DATA_DIR / "connections.json": {"connections": {}},
    }

    for file_path, payload in defaults.items():
        if not file_path.exists():
            file_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

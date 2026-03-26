import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

from backend.api.models import ServiceInfo
from backend.config import settings
from backend.utils.logger import get_logger

logger = get_logger()


class PortDetector:
    def __init__(self, timeout: Optional[float] = None) -> None:
        self.timeout = timeout if timeout is not None else settings.port_scan_timeout
        self.known_services = self._load_known_services()

    def _load_known_services(self) -> List[Dict]:
        path = Path(settings.known_services_json)
        if not path.exists():
            logger.warning("Known services file not found: %s", path)
            return []

        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            logger.exception("Failed to parse known services config.")
            return []

        return payload.get("services", [])

    async def check_port(self, host: str, port: int, timeout: Optional[float] = None) -> bool:
        check_timeout = timeout if timeout is not None else self.timeout
        try:
            conn = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(conn, timeout=check_timeout)
            writer.close()
            await writer.wait_closed()
            return True
        except (asyncio.TimeoutError, OSError):
            return False

    async def detect_local_services(self, host: str = "localhost") -> List[ServiceInfo]:
        now = datetime.now(timezone.utc).isoformat()
        tasks = [
            self.check_port(host, svc.get("port", 0), self.timeout)
            for svc in self.known_services
        ]

        states = await asyncio.gather(*tasks, return_exceptions=True)
        discovered: List[ServiceInfo] = []

        for svc, is_open in zip(self.known_services, states):
            running = bool(is_open) if not isinstance(is_open, Exception) else False
            discovered.append(
                ServiceInfo(
                    name=svc.get("name", f"Service-{svc.get('port', 0)}"),
                    port=svc.get("port", 0),
                    host=host,
                    status="running" if running else "stopped",
                    description=svc.get("description", ""),
                    category=svc.get("category", "custom"),
                    last_checked=now,
                )
            )

        return discovered

    async def get_service_by_port(
        self, port: int, host: str = "localhost"
    ) -> Optional[ServiceInfo]:
        known = next((svc for svc in self.known_services if svc.get("port") == port), None)
        if known:
            running = await self.check_port(host, port)
            return ServiceInfo(
                name=known.get("name", f"Service-{port}"),
                port=port,
                host=host,
                status="running" if running else "stopped",
                description=known.get("description", ""),
                category=known.get("category", "custom"),
            )

        running = await self.check_port(host, port)
        if not running:
            return None

        return ServiceInfo(
            name=f"Custom-{port}",
            port=port,
            host=host,
            status="running",
            description="User discovered custom service",
            category="custom",
        )

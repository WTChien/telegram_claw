from typing import Any, Dict, Optional

import httpx

from backend.utils.logger import get_logger
from backend.utils.security import build_target_url, validate_http_method

logger = get_logger()


class ServiceProxy:
    def __init__(self, retries: int = 2, timeout: float = 30.0) -> None:
        self.retries = retries
        self.timeout = timeout

    async def proxy_request(
        self,
        port: int,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        query_params: Optional[Dict[str, Any]] = None,
        host: str = "localhost",
    ) -> Dict[str, Any]:
        clean_method = validate_http_method(method)
        url = build_target_url(host, port, path)
        clean_headers = {k: v for k, v in (headers or {}).items() if k.lower() != "host"}

        last_error: Optional[str] = None
        for attempt in range(1, self.retries + 2):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.request(
                        clean_method,
                        url,
                        headers=clean_headers,
                        json=json_data,
                        params=query_params,
                    )

                logger.info(
                    "Proxied request %s %s -> %s", clean_method, url, response.status_code
                )

                try:
                    body: Any = response.json()
                except ValueError:
                    body = response.text

                return {
                    "success": True,
                    "status_code": response.status_code,
                    "headers": dict(response.headers),
                    "data": body,
                }
            except httpx.HTTPError as exc:
                last_error = str(exc)
                logger.warning("Proxy attempt %s failed for %s: %s", attempt, url, exc)

        return {
            "success": False,
            "status_code": 502,
            "error": f"Proxy request failed after retries: {last_error}",
        }

    async def check_service_health(self, port: int, host: str = "localhost") -> bool:
        health_candidates = ["/health", "/"]
        for path in health_candidates:
            result = await self.proxy_request(port=port, method="GET", path=path, host=host)
            if result.get("success") and result.get("status_code", 500) < 500:
                return True
        return False

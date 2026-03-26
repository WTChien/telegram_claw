import base64
from typing import Any, Dict, List, Optional

import httpx

from backend.utils.logger import get_logger

logger = get_logger()


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url

    async def list_models(self) -> List[str]:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{self.base_url}/api/tags")
            resp.raise_for_status()
            data = resp.json()
            return [m["name"] for m in data.get("models", [])]

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> str:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(
                f"{self.base_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False},
            )
            resp.raise_for_status()
            return resp.json().get("message", {}).get("content", "")

    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[List[bytes]] = None,
    ) -> str:
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if images:
            payload["images"] = [base64.b64encode(img).decode() for img in images]
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post(f"{self.base_url}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json().get("response", "")

    async def best_model(self, prefer_vision: bool = False) -> str:
        """Return the best available model, optionally preferring a vision model."""
        try:
            models = await self.list_models()
        except Exception:
            return "llama3.2"
        if not models:
            return "llama3.2"
        if prefer_vision:
            vision = [
                m
                for m in models
                if any(k in m.lower() for k in ("llava", "vision", "gemma3", "minicpm", "qwen"))
            ]
            if vision:
                return vision[0]
        return models[0]


ollama_client = OllamaClient()

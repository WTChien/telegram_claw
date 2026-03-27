import base64
import json
import os
import time
from typing import Any, Dict, List, Optional

import httpx

from backend.utils.logger import get_logger

logger = get_logger()


class OllamaClient:
    def __init__(self, base_url: str = "http://localhost:11434") -> None:
        self.base_url = base_url
        self.connect_timeout = float(os.getenv("OLLAMA_CONNECT_TIMEOUT", "10"))
        self.list_timeout = float(os.getenv("OLLAMA_LIST_TIMEOUT", "20"))
        self.chat_timeout = float(os.getenv("OLLAMA_CHAT_TIMEOUT", "300"))
        self.generate_timeout = float(os.getenv("OLLAMA_GENERATE_TIMEOUT", "600"))
        self.default_model = os.getenv("OLLAMA_DEFAULT_MODEL", "").strip()
        self.default_vision_model = os.getenv("OLLAMA_DEFAULT_VISION_MODEL", "").strip()

    def _timeout(self, seconds: float) -> httpx.Timeout:
        return httpx.Timeout(
            connect=self.connect_timeout,
            read=seconds,
            write=seconds,
            pool=None,
        )

    @staticmethod
    def _to_ms_from_ns(value: Any) -> Optional[float]:
        if isinstance(value, (int, float)):
            return float(value) / 1_000_000
        return None

    def _build_metrics(
        self,
        payload: Dict[str, Any],
        fallback_elapsed_ms: float,
        requested_model: str,
    ) -> Dict[str, Any]:
        prompt_tokens = int(payload.get("prompt_eval_count") or 0)
        completion_tokens = int(payload.get("eval_count") or 0)
        total_tokens = prompt_tokens + completion_tokens

        api_total_ms = self._to_ms_from_ns(payload.get("total_duration"))

        return {
            "model": str(payload.get("model") or requested_model),
            "elapsed_ms": round(api_total_ms if api_total_ms is not None else fallback_elapsed_ms, 1),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total_tokens,
        }

    @staticmethod
    def _match_model(models: List[str], preferred: str) -> Optional[str]:
        if not preferred:
            return None

        preferred_lower = preferred.lower()
        exact = next((m for m in models if m.lower() == preferred_lower), None)
        if exact:
            return exact

        # Allow prefix match, e.g. "qwen3.5" to match "qwen3.5:9b".
        return next((m for m in models if m.lower().startswith(preferred_lower)), None)

    async def list_models(self) -> List[str]:
        started_at = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout(self.list_timeout)) as client:
                resp = await client.get(f"{self.base_url}/api/tags")
                resp.raise_for_status()
                data = resp.json()
                models = [m["name"] for m in data.get("models", [])]
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                logger.info("Ollama list_models completed in %.1f ms (count=%s)", elapsed_ms, len(models))
                return models
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.exception("Ollama list_models failed after %.1f ms", elapsed_ms)
            raise

    async def chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        started_at = time.perf_counter()
        try:
            async with httpx.AsyncClient(timeout=self._timeout(self.chat_timeout)) as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json={"model": model, "messages": messages, "stream": False},
                )
                resp.raise_for_status()
                data = resp.json()
                content = data.get("message", {}).get("content", "")
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                metrics = self._build_metrics(data, elapsed_ms, model)
                logger.info(
                    "Ollama chat completed in %.1f ms (model=%s, messages=%s, tokens=%s)",
                    metrics["elapsed_ms"],
                    metrics["model"],
                    len(messages),
                    metrics["total_tokens"],
                )
                return {"content": content, "metrics": metrics}
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.exception("Ollama chat failed after %.1f ms (model=%s)", elapsed_ms, model)
            raise

    async def stream_chat(
        self,
        model: str,
        messages: List[Dict[str, Any]],
    ):
        started_at = time.perf_counter()
        collected_parts: List[str] = []
        try:
            async with httpx.AsyncClient(timeout=self._timeout(self.chat_timeout)) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/api/chat",
                    json={"model": model, "messages": messages, "stream": True},
                ) as resp:
                    resp.raise_for_status()

                    async for line in resp.aiter_lines():
                        if not line:
                            continue

                        data = json.loads(line)
                        content = data.get("message", {}).get("content", "")
                        if content:
                            collected_parts.append(content)
                            yield {"type": "chunk", "content": content}

                        if data.get("done"):
                            elapsed_ms = (time.perf_counter() - started_at) * 1000
                            metrics = self._build_metrics(data, elapsed_ms, model)
                            full_content = "".join(collected_parts)
                            logger.info(
                                "Ollama stream_chat completed in %.1f ms (model=%s, messages=%s, tokens=%s)",
                                metrics["elapsed_ms"],
                                metrics["model"],
                                len(messages),
                                metrics["total_tokens"],
                            )
                            yield {
                                "type": "done",
                                "content": full_content,
                                "metrics": metrics,
                            }
                            return
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.exception("Ollama stream_chat failed after %.1f ms (model=%s)", elapsed_ms, model)
            raise

    async def generate(
        self,
        model: str,
        prompt: str,
        images: Optional[List[bytes]] = None,
    ) -> Dict[str, Any]:
        started_at = time.perf_counter()
        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
        }
        if images:
            payload["images"] = [base64.b64encode(img).decode() for img in images]
        try:
            async with httpx.AsyncClient(timeout=self._timeout(self.generate_timeout)) as client:
                resp = await client.post(f"{self.base_url}/api/generate", json=payload)
                resp.raise_for_status()
                data = resp.json()
                response_text = data.get("response", "")
                elapsed_ms = (time.perf_counter() - started_at) * 1000
                metrics = self._build_metrics(data, elapsed_ms, model)
                logger.info(
                    "Ollama generate completed in %.1f ms (model=%s, images=%s, tokens=%s)",
                    metrics["elapsed_ms"],
                    metrics["model"],
                    len(images or []),
                    metrics["total_tokens"],
                )
                return {"content": response_text, "metrics": metrics}
        except Exception:
            elapsed_ms = (time.perf_counter() - started_at) * 1000
            logger.exception(
                "Ollama generate failed after %.1f ms (model=%s, images=%s)",
                elapsed_ms,
                model,
                len(images or []),
            )
            raise

    async def best_model(self, prefer_vision: bool = False) -> str:
        """Return the best available model, optionally preferring a vision model."""
        try:
            models = await self.list_models()
        except Exception:
            return "llama3.2"
        if not models:
            return "llama3.2"

        if prefer_vision:
            pinned = self._match_model(models, self.default_vision_model)
            if pinned:
                return pinned

            vision = [
                m
                for m in models
                if any(k in m.lower() for k in ("vl", "vision", "llava", "gemma3", "minicpm", "qwen"))
            ]
            if vision:
                return vision[0]

        pinned = self._match_model(models, self.default_model)
        if pinned:
            return pinned

        # For text chat, avoid selecting heavyweight vision models by default.
        non_vision = [
            m
            for m in models
            if not any(k in m.lower() for k in ("vl", "vision", "llava", "minicpm"))
        ]

        if non_vision:
            # Prefer common text model families first.
            for key in ("qwen3.5", "qwen", "deepseek", "llama3", "mistral"):
                choice = next((m for m in non_vision if key in m.lower()), None)
                if choice:
                    return choice
            return non_vision[0]

        return models[0]


ollama_client = OllamaClient()

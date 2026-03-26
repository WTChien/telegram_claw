from typing import Any, Dict, List

from fastapi import APIRouter, HTTPException, Query

from backend.api.models import ChatMessageRequest
from backend.services.service_proxy import ServiceProxy
from backend.services.state import state_store

router = APIRouter(prefix="/api/chat", tags=["chat"])
proxy = ServiceProxy()


def _extract_models(payload: Any) -> List[str]:
    if isinstance(payload, dict):
        if "models" in payload and isinstance(payload["models"], list):
            models = []
            for item in payload["models"]:
                if isinstance(item, dict):
                    name = item.get("name") or item.get("id")
                    if name:
                        models.append(str(name))
                elif isinstance(item, str):
                    models.append(item)
            return models

        if "data" in payload and isinstance(payload["data"], list):
            models = []
            for item in payload["data"]:
                if isinstance(item, dict) and item.get("id"):
                    models.append(str(item["id"]))
            return models

    return []


@router.post("/message")
async def send_chat_message(payload: ChatMessageRequest):
    connection = state_store.get_connection(payload.user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="No connected service for user")

    body: Dict[str, Any] = {
        "message": payload.message,
    }
    if payload.model:
        body["model"] = payload.model
    if payload.extra_payload:
        body.update(payload.extra_payload)

    result = await proxy.proxy_request(
        port=connection.port,
        method="POST",
        path=payload.target_path,
        json_data=body,
    )

    if not result.get("success"):
        raise HTTPException(status_code=502, detail=result.get("error", "Proxy failed"))

    state_store.increment_request_count(payload.user_id)
    return {"success": True, "response": result.get("data")}


@router.get("/models")
async def get_models(user_id: str = Query(default="web-user")):
    connection = state_store.get_connection(user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="No connected service for user")

    candidates = ["/api/tags", "/v1/models", "/models"]
    for path in candidates:
        result = await proxy.proxy_request(
            port=connection.port,
            method="GET",
            path=path,
        )
        if not result.get("success"):
            continue

        models = _extract_models(result.get("data"))
        if models:
            return {"models": models, "source": path}

    return {"models": [], "source": None}

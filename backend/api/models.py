from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ServiceInfo(BaseModel):
    name: str
    port: int
    host: str = "localhost"
    status: str = "stopped"
    description: str = ""
    category: str = "custom"
    last_checked: str = Field(default_factory=utc_now_iso)


class ServiceConnection(BaseModel):
    user_id: str
    port: int
    service_name: str
    connected_at: str = Field(default_factory=utc_now_iso)
    requests_count: int = 0


class UserServicePreference(BaseModel):
    user_id: str
    preferred_port: int
    preferred_service: str
    saved_at: str = Field(default_factory=utc_now_iso)


class ConnectServiceRequest(BaseModel):
    user_id: str = "web-user"
    port: int


class ProxyRequest(BaseModel):
    user_id: str = "web-user"
    port: Optional[int] = None
    method: str = "GET"
    path: str = "/"
    headers: Optional[Dict[str, str]] = None
    json_data: Optional[Dict[str, Any]] = None
    query_params: Optional[Dict[str, Any]] = None


class SavePreferenceRequest(BaseModel):
    user_id: str
    preferred_port: int
    preferred_service: str


class ChatMessageRequest(BaseModel):
    user_id: str = "web-user"
    message: str
    model: Optional[str] = None
    target_path: str = "/api/chat"
    extra_payload: Optional[Dict[str, Any]] = None


class ChatMessageResponse(BaseModel):
    success: bool
    response: Any


class ModelsResponse(BaseModel):
    models: List[str]

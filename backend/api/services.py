from fastapi import APIRouter, HTTPException, Query

from backend.api.models import (
    ConnectServiceRequest,
    ProxyRequest,
    SavePreferenceRequest,
    ServiceConnection,
    UserServicePreference,
)
from backend.services.port_detector import PortDetector
from backend.services.service_proxy import ServiceProxy
from backend.services.state import state_store

router = APIRouter(prefix="/api/services", tags=["services"])

detector = PortDetector()
proxy = ServiceProxy()


@router.get("/list")
async def list_known_services():
    return {"services": detector.known_services}


@router.get("/scan")
async def scan_services(host: str = "localhost"):
    services = await detector.detect_local_services(host=host)
    return {"services": [service.model_dump() for service in services]}


@router.post("/connect")
async def connect_service(payload: ConnectServiceRequest):
    service = await detector.get_service_by_port(payload.port)
    if not service:
        raise HTTPException(status_code=404, detail=f"No running service found on port {payload.port}")

    connection = ServiceConnection(
        user_id=payload.user_id,
        port=service.port,
        service_name=service.name,
    )
    state_store.save_connection(connection)

    preference = UserServicePreference(
        user_id=payload.user_id,
        preferred_port=service.port,
        preferred_service=service.name,
    )
    state_store.save_preference(preference)

    return {
        "message": "Connected successfully",
        "connection": connection.model_dump(),
        "service": service.model_dump(),
    }


@router.get("/current")
async def get_current_service(user_id: str = Query(default="web-user")):
    connection = state_store.get_connection(user_id)
    if not connection:
        raise HTTPException(status_code=404, detail="No active connection for this user")
    return {"connection": connection.model_dump()}


@router.post("/proxy")
async def proxy_to_current(payload: ProxyRequest):
    target_port = payload.port
    if target_port is None:
        current = state_store.get_connection(payload.user_id)
        if not current:
            raise HTTPException(status_code=404, detail="No active connection. Connect first.")
        target_port = current.port

    result = await proxy.proxy_request(
        port=target_port,
        method=payload.method,
        path=payload.path,
        headers=payload.headers,
        json_data=payload.json_data,
        query_params=payload.query_params,
    )

    if result.get("success"):
        state_store.increment_request_count(payload.user_id)

    return result


@router.get("/user/preference")
async def get_user_preference(user_id: str = Query(default="web-user")):
    pref = state_store.get_preference(user_id)
    if not pref:
        raise HTTPException(status_code=404, detail="Preference not found")
    return {"preference": pref.model_dump()}


@router.post("/user/preference")
async def save_user_preference(payload: SavePreferenceRequest):
    pref = UserServicePreference(
        user_id=payload.user_id,
        preferred_port=payload.preferred_port,
        preferred_service=payload.preferred_service,
    )
    state_store.save_preference(pref)
    return {"message": "Preference saved", "preference": pref.model_dump()}

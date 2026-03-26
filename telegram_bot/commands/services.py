import os
from typing import Any, Dict, List

import httpx
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes


def _api_base_url() -> str:
    return os.getenv("NANOCLAW_API_BASE", "http://localhost:8000")


async def _api_get(path: str) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.get(f"{_api_base_url()}{path}")
        response.raise_for_status()
        return response.json()


async def _api_post(path: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    async with httpx.AsyncClient(timeout=20) as client:
        response = await client.post(f"{_api_base_url()}{path}", json=payload)
        response.raise_for_status()
        return response.json()


def _to_user_id(update: Update) -> str:
    if not update.effective_user:
        return "telegram-unknown"
    return str(update.effective_user.id)


async def cmd_services(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    try:
        data = await _api_get("/api/services/scan")
    except Exception as exc:
        await update.message.reply_text(f"掃描失敗: {exc}")
        return

    services: List[Dict[str, Any]] = data.get("services", [])
    if not services:
        await update.message.reply_text("目前沒有偵測到可用服務")
        return

    lines = ["可用服務:"]
    keyboard = []
    for svc in services:
        status = svc.get("status", "unknown")
        lines.append(f"- {svc.get('name')}:{svc.get('port')} [{status}]")
        if status == "running":
            keyboard.append(
                [
                    InlineKeyboardButton(
                        text=f"連接 {svc.get('name')}:{svc.get('port')}",
                        callback_data=f"connect:{svc.get('port')}",
                    )
                ]
            )

    markup = InlineKeyboardMarkup(keyboard) if keyboard else None
    await update.message.reply_text("\n".join(lines), reply_markup=markup)


async def cmd_scan(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await cmd_services(update, context)


async def cmd_current(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    user_id = _to_user_id(update)
    try:
        data = await _api_get(f"/api/services/current?user_id={user_id}")
        conn = data.get("connection", {})
        await update.message.reply_text(
            f"當前服務: {conn.get('service_name')}:{conn.get('port')}\n"
            f"請求次數: {conn.get('requests_count', 0)}"
        )
    except Exception as exc:
        await update.message.reply_text(f"尚未連接服務: {exc}")


async def on_connect_button(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    query = update.callback_query
    await query.answer()

    if not query.data or not query.data.startswith("connect:"):
        return

    try:
        port = int(query.data.split(":", maxsplit=1)[1])
    except ValueError:
        await query.edit_message_text("無效的端口")
        return

    user_id = _to_user_id(update)
    try:
        result = await _api_post(
            "/api/services/connect", {"user_id": user_id, "port": port}
        )
        service = result.get("service", {})
        await query.edit_message_text(
            f"已連接: {service.get('name')}:{service.get('port')}"
        )
    except Exception as exc:
        await query.edit_message_text(f"連接失敗: {exc}")

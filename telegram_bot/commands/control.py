import asyncio
import logging
import os
import io
import re
import traceback

import httpx
from telegram import Update
from telegram.constants import ParseMode
from telegram.error import BadRequest, RetryAfter
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

from backend.services.computer_control import computer
from backend.services.ollama_client import ollama_client

ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "")


def _extract_screen_arg(args: list[str]) -> tuple[int | None, list[str]]:
    """Parse optional screen selector from command args.

    Accepted forms:
    - 2
    - screen2
    - screen:2
    - screen=2
    """
    if not args:
        return None, args

    token = args[0].strip().lower()
    index: int | None = None

    if token.isdigit():
        index = int(token)
    elif token.startswith("screen"):
        suffix = token[len("screen") :]
        if suffix.startswith((":", "=")):
            suffix = suffix[1:]
        if suffix.isdigit():
            index = int(suffix)

    if index is None:
        return None, args

    return index, args[1:]


def _is_admin(update: Update) -> bool:
    if not ADMIN_USER_ID:
        return True  # 未設定 ADMIN_USER_ID 時不限制
    return str(update.effective_user.id) == ADMIN_USER_ID


def _sanitize_markdown_for_telegram(text: str) -> str:
    lines = text.splitlines()
    normalized_lines = []
    in_code_block = False

    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            normalized_lines.append(line)
            continue

        if not in_code_block:
            match = re.match(r"^(#{1,6})\s+(.+)$", line)
            if match:
                title = match.group(2).strip()
                normalized_lines.append(f"*{title}*")
                continue

        normalized_lines.append(line)

    # Close any unclosed code block so Telegram doesn't reject it
    if in_code_block:
        normalized_lines.append("```")

    result = "\n".join(normalized_lines)
    return _balance_inline_markers(result)


def _balance_inline_markers(text: str) -> str:
    """Escape the last unbalanced * or _ in each non-code line."""
    lines = text.splitlines()
    result_lines = []
    in_code_block = False

    for line in lines:
        if line.strip().startswith("```"):
            in_code_block = not in_code_block
            result_lines.append(line)
            continue

        if in_code_block:
            result_lines.append(line)
            continue

        # Split on inline code spans to avoid touching them
        parts = re.split(r'(`[^`]*`)', line)
        non_code = ''.join(p for i, p in enumerate(parts) if i % 2 == 0)

        if non_code.count('*') % 2 != 0:
            for i in range(len(parts) - 1, -1, -1):
                if i % 2 == 0 and '*' in parts[i]:
                    idx = parts[i].rfind('*')
                    parts[i] = parts[i][:idx] + '\\*' + parts[i][idx + 1:]
                    break

        if non_code.count('_') % 2 != 0:
            for i in range(len(parts) - 1, -1, -1):
                if i % 2 == 0 and '_' in parts[i]:
                    idx = parts[i].rfind('_')
                    parts[i] = parts[i][:idx] + '\\_' + parts[i][idx + 1:]
                    break

        result_lines.append(''.join(parts))

    return '\n'.join(result_lines)


async def _safe_edit_text(msg, text: str) -> None:
    """Edit a message, silently swallowing all Telegram errors."""
    text = _sanitize_markdown_for_telegram(text)
    safe_text = text[:3900] + "\n...（已截斷）" if len(text) > 3900 else text
    try:
        await msg.edit_text(safe_text, parse_mode=ParseMode.MARKDOWN)
    except RetryAfter as exc:
        logger.warning("edit_text flood-control, skipping update (retry_after=%ss)", exc.retry_after)
    except BadRequest:
        # Markdown parse error – retry as plain text
        try:
            await msg.edit_text(safe_text)
        except RetryAfter as exc:
            logger.warning("edit_text (plain) flood-control, skipping update (retry_after=%ss)", exc.retry_after)
        except Exception as exc:
            logger.debug("edit_text (plain) failed: %s", exc)
    except Exception as exc:
        try:
            await msg.edit_text(safe_text)
        except Exception as inner:
            logger.debug("edit_text fallback failed: %s", inner)


async def _safe_reply_text(update: Update, text: str) -> None:
    text = _sanitize_markdown_for_telegram(text)
    safe_text = text[:3900] + "\n...（已截斷）" if len(text) > 3900 else text
    try:
        await update.message.reply_text(safe_text, parse_mode=ParseMode.MARKDOWN)
    except RetryAfter as exc:
        logger.warning("reply_text flood-control (retry_after=%ss)", exc.retry_after)
    except BadRequest:
        try:
            await update.message.reply_text(safe_text)
        except Exception as exc:
            logger.debug("reply_text (plain) failed: %s", exc)
    except Exception:
        try:
            await update.message.reply_text(safe_text)
        except Exception as exc:
            logger.debug("reply_text fallback failed: %s", exc)


def _format_metrics(metrics: dict) -> str:
    model = metrics.get("model", "unknown")
    elapsed_ms = float(metrics.get("elapsed_ms", 0.0) or 0.0)
    total_tokens = int(metrics.get("total_tokens", 0) or 0)
    prompt_tokens = int(metrics.get("prompt_tokens", 0) or 0)
    completion_tokens = int(metrics.get("completion_tokens", 0) or 0)

    return (
        f"模型: {model}\n"
        f"耗時: {elapsed_ms / 1000:.2f}s\n"
        f"Token: {total_tokens} (prompt={prompt_tokens}, completion={completion_tokens})"
    )


async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """截取目前螢幕畫面並回傳。"""
    _ = context
    msg = await update.message.reply_text("截圖中...")
    try:
        screenshots = await computer.take_screenshots()
        total = len(screenshots)
        for index, img_bytes in enumerate(screenshots, start=1):
            await update.message.reply_document(
                document=io.BytesIO(img_bytes),
                filename=f"screenshot-display-{index}.png",
                caption=(
                    f"目前螢幕截圖 {index}/{total}"
                    if total > 1
                    else "目前螢幕截圖"
                ),
            )
        await msg.delete()
    except Exception as exc:
        tb = traceback.format_exc()
        err_type = type(exc).__name__
        detail = f"截圖失敗\n\n[{err_type}] {exc}\n\n{tb}"
        await _safe_edit_text(msg, detail)


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """傳問題給本地 Ollama 模型並回傳答案。用法: /ask <問題>"""
    question = " ".join(context.args) if context.args else ""
    if not question:
        await _safe_reply_text(update, "用法: /ask <問題>\n例如: /ask 幫我寫一個 Python hello world")
        return

    msg = await update.message.reply_text("正在詢問 Ollama，請稍候...")
    try:
        selected_model = await ollama_client.best_model(prefer_vision=False)
        result = await ollama_client.chat(
            model=selected_model,
            messages=[{"role": "user", "content": question}],
        )
        answer = result.get("content", "")
        metrics = result.get("metrics", {"model": selected_model})
        stats = _format_metrics(metrics)

        reply = f"{answer}\n\n---\n{stats}" if answer else f"（Ollama 無回應）\n\n---\n{stats}"
        await _safe_edit_text(msg, reply)
    except Exception as exc:
        tb = traceback.format_exc()
        err_type = type(exc).__name__

        ollama_body = ""
        if isinstance(exc, httpx.HTTPStatusError):
            try:
                ollama_body = f"\nOllama response body: {exc.response.text[:500]}"
            except Exception:
                pass

        detail = (
            f"Ollama 錯誤\n\n"
            f"[{err_type}] {exc}{ollama_body}\n\n"
            f"{tb}"
        )
        await _safe_edit_text(msg, detail)


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """執行 shell 指令並回傳結果（僅限管理員）。用法: /run <指令>"""
    if not _is_admin(update):
        await update.message.reply_text("此指令僅限管理員使用")
        return

    cmd = " ".join(context.args) if context.args else ""
    if not cmd:
        await _safe_reply_text(update, "用法: /run <shell 指令>\n例如: /run ls ~/Desktop")
        return

    msg = await update.message.reply_text(f"執行: `{cmd}`")
    try:
        code, stdout, stderr = await computer.run_command(cmd)
        output = stdout or stderr or "（無輸出）"
        result = f"退出碼: {code}\n\n{output}"
        await _safe_edit_text(msg, result)
    except Exception as exc:
        await _safe_edit_text(msg, f"執行失敗: {exc}")


async def cmd_control(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """截圖後交給 Ollama vision 模型分析並給出操作建議（僅限管理員）。"""
    if not _is_admin(update):
        await update.message.reply_text("此指令僅限管理員使用")
        return

    selected_screen, remaining_args = _extract_screen_arg(list(context.args or []))
    instruction = " ".join(remaining_args) if remaining_args else ""
    if not instruction:
        await _safe_reply_text(
            update,
            "用法: /control [螢幕編號] <指令>\n"
            "例如: /control 2 幫我截圖並告訴我現在螢幕上有什麼\n"
            "或: /control screen2 幫我找出右邊螢幕的重點"
        )
        return

    msg = await update.message.reply_text("截圖並分析中...")
    try:
        screenshots = await computer.take_screenshots()
        total_screens = len(screenshots)

        if selected_screen is not None:
            if selected_screen < 1 or selected_screen > total_screens:
                await _safe_edit_text(
                    msg,
                    f"分析失敗: 無效螢幕編號 {selected_screen}，目前可用範圍為 1-{total_screens}"
                )
                return
            selected_images = [screenshots[selected_screen - 1]]
            selection_hint = f"螢幕 {selected_screen}/{total_screens}"
        else:
            selected_images = screenshots
            selection_hint = f"全部螢幕，共 {total_screens} 張"

        selected_model = await ollama_client.best_model(prefer_vision=True)
        await msg.edit_text(f"截圖完成（{selection_hint}），正在用 {selected_model} 分析...")

        prompt = (
            f"你是一個智慧型電腦控制助理，使用繁體中文回答。\n"
            f"使用者指令: {instruction}\n\n"
            f"請根據截圖內容：\n"
            f"1. 描述目前螢幕顯示什麼\n"
            f"2. 給出完成指令所需的具體操作步驟\n"
            f"3. 如果需要執行指令，請明確說明要用 /run 執行什麼命令"
        )
        result = await ollama_client.generate(
            model=selected_model,
            prompt=prompt,
            images=selected_images,
        )
        answer = result.get("content", "")
        metrics = result.get("metrics", {"model": selected_model})
        stats = _format_metrics(metrics)
        reply = answer if answer else "（模型無回應，請確認是否有安裝 vision 模型）"

        for index, img_bytes in enumerate(selected_images, start=1):
            await update.message.reply_document(
                document=io.BytesIO(img_bytes),
                filename=f"control-display-{index}.png",
                caption=f"分析用截圖 {index}/{len(selected_images)}",
            )
        await _safe_reply_text(update, f"分析結果:\n\n{reply}\n\n---\n{stats}")
        await msg.delete()
    except Exception as exc:
        tb = traceback.format_exc()
        err_type = type(exc).__name__

        # 若是 httpx HTTP 錯誤，把 Ollama 回傳的實際 body 也印出來
        ollama_body = ""
        if isinstance(exc, httpx.HTTPStatusError):
            try:
                ollama_body = f"\nOllama response body: {exc.response.text[:500]}"
            except Exception:
                pass

        detail = (
            f"分析失敗\n\n"
            f"[{err_type}] {exc}{ollama_body}\n\n"
            f"{tb}"
        )
        await _safe_edit_text(msg, detail)


async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """開啟 App 或網址（僅限管理員）。用法: /open <app名稱或網址>"""
    if not _is_admin(update):
        await update.message.reply_text("此指令僅限管理員使用")
        return

    target = " ".join(context.args) if context.args else ""
    if not target:
        await _safe_reply_text(update, "用法: /open <App名稱或網址>\n例如: /open Safari 或 /open https://google.com")
        return

    try:
        if target.startswith("http"):
            await computer.open_url(target)
            await _safe_reply_text(update, f"已開啟網址: {target}")
        else:
            await computer.open_app(target)
            await _safe_reply_text(update, f"已開啟: {target}")
    except Exception as exc:
        await _safe_reply_text(update, f"開啟失敗: {exc}")

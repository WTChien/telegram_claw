import os

from telegram import Update
from telegram.ext import ContextTypes

from backend.services.computer_control import computer
from backend.services.ollama_client import ollama_client

ADMIN_USER_ID = os.getenv("ADMIN_USER_ID", "")


def _is_admin(update: Update) -> bool:
    if not ADMIN_USER_ID:
        return True  # 未設定 ADMIN_USER_ID 時不限制
    return str(update.effective_user.id) == ADMIN_USER_ID


async def cmd_screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """截取目前螢幕畫面並回傳。"""
    _ = context
    msg = await update.message.reply_text("截圖中...")
    try:
        img_bytes = await computer.take_screenshot()
        await update.message.reply_photo(photo=img_bytes, caption="目前螢幕截圖")
        await msg.delete()
    except Exception as exc:
        await msg.edit_text(f"截圖失敗: {exc}")


async def cmd_ask(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """傳問題給本地 Ollama 模型並回傳答案。用法: /ask <問題>"""
    question = " ".join(context.args) if context.args else ""
    if not question:
        await update.message.reply_text("用法: /ask <問題>\n例如: /ask 幫我寫一個 Python hello world")
        return

    msg = await update.message.reply_text("正在詢問 Ollama，請稍候...")
    try:
        model = await ollama_client.best_model(prefer_vision=False)
        answer = await ollama_client.chat(
            model=model,
            messages=[{"role": "user", "content": question}],
        )
        reply = f"**{model}** 回答:\n\n{answer}" if answer else "（Ollama 無回應）"
        # Telegram 訊息上限 4096 字
        if len(reply) > 4000:
            reply = reply[:4000] + "\n\n...（已截斷）"
        await msg.edit_text(reply)
    except Exception as exc:
        await msg.edit_text(f"Ollama 錯誤: {exc}\n\n請確認 Ollama 正在 localhost:11434 運行")


async def cmd_run(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """執行 shell 指令並回傳結果（僅限管理員）。用法: /run <指令>"""
    if not _is_admin(update):
        await update.message.reply_text("此指令僅限管理員使用")
        return

    cmd = " ".join(context.args) if context.args else ""
    if not cmd:
        await update.message.reply_text("用法: /run <shell 指令>\n例如: /run ls ~/Desktop")
        return

    msg = await update.message.reply_text(f"執行: `{cmd}`")
    try:
        code, stdout, stderr = await computer.run_command(cmd)
        output = stdout or stderr or "（無輸出）"
        if len(output) > 3500:
            output = output[:3500] + "\n...（已截斷）"
        result = f"退出碼: {code}\n\n{output}"
        await msg.edit_text(result)
    except Exception as exc:
        await msg.edit_text(f"執行失敗: {exc}")


async def cmd_control(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """截圖後交給 Ollama vision 模型分析並給出操作建議（僅限管理員）。用法: /control <指令>"""
    if not _is_admin(update):
        await update.message.reply_text("此指令僅限管理員使用")
        return

    instruction = " ".join(context.args) if context.args else ""
    if not instruction:
        await update.message.reply_text(
            "用法: /control <指令>\n"
            "例如: /control 幫我截圖並告訴我現在螢幕上有什麼"
        )
        return

    msg = await update.message.reply_text("截圖並分析中...")
    try:
        img_bytes = await computer.take_screenshot()
        model = await ollama_client.best_model(prefer_vision=True)
        await msg.edit_text(f"截圖完成，正在用 {model} 分析...")

        prompt = (
            f"你是一個智慧型電腦控制助理，使用繁體中文回答。\n"
            f"使用者指令: {instruction}\n\n"
            f"請根據截圖內容：\n"
            f"1. 描述目前螢幕顯示什麼\n"
            f"2. 給出完成指令所需的具體操作步驟\n"
            f"3. 如果需要執行指令，請明確說明要用 /run 執行什麼命令"
        )
        answer = await ollama_client.generate(
            model=model,
            prompt=prompt,
            images=[img_bytes],
        )
        reply = answer if answer else "（模型無回應，請確認是否有安裝 vision 模型）"
        if len(reply) > 900:
            reply = reply[:900] + "\n...（已截斷）"

        await update.message.reply_photo(
            photo=img_bytes,
            caption=f"**{model}** 分析結果:\n\n{reply}",
        )
        await msg.delete()
    except Exception as exc:
        await msg.edit_text(
            f"分析失敗: {exc}\n\n"
            f"提示: /control 需要 vision 模型，可先用:\n"
            f"`ollama pull llava` 或 `ollama pull llama3.2-vision`"
        )


async def cmd_open(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """開啟 App 或網址（僅限管理員）。用法: /open <app名稱或網址>"""
    if not _is_admin(update):
        await update.message.reply_text("此指令僅限管理員使用")
        return

    target = " ".join(context.args) if context.args else ""
    if not target:
        await update.message.reply_text("用法: /open <App名稱或網址>\n例如: /open Safari 或 /open https://google.com")
        return

    try:
        if target.startswith("http"):
            await computer.open_url(target)
            await update.message.reply_text(f"已開啟網址: {target}")
        else:
            await computer.open_app(target)
            await update.message.reply_text(f"已開啟: {target}")
    except Exception as exc:
        await update.message.reply_text(f"開啟失敗: {exc}")

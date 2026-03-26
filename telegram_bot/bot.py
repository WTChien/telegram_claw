import asyncio
import os

from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
)

from telegram_bot.commands.services import (
    cmd_current,
    cmd_scan,
    cmd_services,
    on_connect_button,
)
from telegram_bot.commands.control import (
    cmd_screenshot,
    cmd_ask,
    cmd_run,
    cmd_control,
    cmd_open,
)

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    msg = (
        "歡迎使用 nanoclaw Bot\n\n"
        "服務管理:\n"
        "/services - 掃描並列出服務\n"
        "/scan - 主動掃描本機服務\n"
        "/current - 查看當前連接\n\n"
        "電腦控制 (Ollama):\n"
        "/screenshot - 截取螢幕畫面\n"
        "/ask <問題> - 詢問本地 Ollama 模型\n"
        "/control <指令> - 截圖並讓 Ollama 分析操作\n"
        "/run <指令> - 執行 shell 指令\n"
        "/open <App或網址> - 開啟應用程式或網址"
    )
    await update.message.reply_text(msg)


def build_app() -> Application:
    if not BOT_TOKEN:
        raise RuntimeError("TELEGRAM_BOT_TOKEN is not configured")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", cmd_start))
    app.add_handler(CommandHandler("services", cmd_services))
    app.add_handler(CommandHandler("scan", cmd_scan))
    app.add_handler(CommandHandler("current", cmd_current))
    app.add_handler(CallbackQueryHandler(on_connect_button, pattern=r"^connect:"))
    # 電腦控制命令
    app.add_handler(CommandHandler("screenshot", cmd_screenshot))
    app.add_handler(CommandHandler("ask", cmd_ask))
    app.add_handler(CommandHandler("run", cmd_run))
    app.add_handler(CommandHandler("control", cmd_control))
    app.add_handler(CommandHandler("open", cmd_open))
    return app


async def run_bot() -> None:
    app = build_app()
    await app.initialize()
    await app.start()
    await app.updater.start_polling()

    try:
        while True:
            await asyncio.sleep(1)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()


if __name__ == "__main__":
    asyncio.run(run_bot())

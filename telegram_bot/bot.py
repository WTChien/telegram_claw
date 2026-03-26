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

load_dotenv()
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")


async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    _ = context
    msg = (
        "歡迎使用 nanoclaw Bot\n\n"
        "可用命令:\n"
        "/services - 掃描並列出服務\n"
        "/scan - 主動掃描本機服務\n"
        "/current - 查看當前連接"
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

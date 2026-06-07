from __future__ import annotations

import os

from telegram.ext import Application

from ..config import load_environment
from .handlers import WELCOME, register_handlers


def run_telegram_bot() -> None:
    load_environment()
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    owner_id = os.getenv("TELEGRAM_OWNER_ID")
    if not token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN before starting Telegram mode.")

    async def post_init(application: Application) -> None:
        if owner_id:
            await application.bot.send_message(chat_id=owner_id, text=WELCOME)

    application = Application.builder().token(token).post_init(post_init).build()
    register_handlers(application)
    application.run_polling()

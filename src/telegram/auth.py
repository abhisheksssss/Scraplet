from __future__ import annotations

import os


def is_owner(chat_id: int | str | None) -> bool:
    owner = os.getenv("TELEGRAM_OWNER_ID", "").strip()
    return bool(owner and str(chat_id) == owner)

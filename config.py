import os
from dataclasses import dataclass
from dotenv import load_dotenv


@dataclass
class Settings:
    bot_token: str
    admin_ids: list[int]
    db_path: str = "bot.db"
    channel_id: str | None = None


def load_settings() -> Settings:
    load_dotenv()

    token = os.getenv("BOT_TOKEN")
    if not token:
        raise RuntimeError("Не задан BOT_TOKEN в .env")

    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    admin_ids: list[int] = []
    for part in admin_ids_raw.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            admin_ids.append(int(part))
        except ValueError:
            raise RuntimeError(f"Некорректный admin id: {part}")

    if not admin_ids:
        raise RuntimeError("Список ADMIN_IDS пуст. Укажите хотя бы один ID администратора.")

    channel_id = os.getenv("CHANNEL_ID")  # можно указать @username или -100...

    return Settings(bot_token=token, admin_ids=admin_ids, channel_id=channel_id)


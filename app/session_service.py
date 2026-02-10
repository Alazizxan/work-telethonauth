from pathlib import Path

SESSIONS_DIR = Path("storage/sessions")


def get_session_path(bot_id: int, user_id: int):
    path = SESSIONS_DIR / str(bot_id)
    path.mkdir(parents=True, exist_ok=True)
    return str(path / f"{user_id}")

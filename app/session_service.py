from pathlib import Path

BASE_DIR = Path("storage/owners")


def get_session_path(owner_id: int, bot_id: int, user_id: int):
    """
    storage/owners/{ownerId}/bots/{botId}/sessions/{userId}.session
    """

    path = (
        BASE_DIR
        / str(owner_id)
        / "bots"
        / str(bot_id)
        / "sessions"
    )

    path.mkdir(parents=True, exist_ok=True)

    return str(path / f"{user_id}")

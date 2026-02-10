from .db import get_texts


async def load_texts(bot_id: int):
    return await get_texts(bot_id)

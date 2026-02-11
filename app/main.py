import asyncio
from fastapi import FastAPI

from .config import REDIS_URL
from .db import init_db, get_active_bots
from .bot_manager import start_bot

app = FastAPI()


@app.on_event("startup")
async def startup():
    await init_db()
    bot_rows = await get_active_bots()

    for b in bot_rows:
        bot_data = await start_bot(
            b["id"],
            b["token"],
            b["ownerId"],
            REDIS_URL
        )

        bot = bot_data["bot"]
        dp = bot_data["dp"]

        # polling start
        asyncio.create_task(dp.start_polling(bot))

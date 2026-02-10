import asyncio
from fastapi import FastAPI, Request
from aiogram.types import Update

from .config import REDIS_URL, BASE_WEBHOOK_URL
from .db import init_db, get_active_bots
from .bot_manager import start_bot, bots

app = FastAPI()


@app.on_event("startup")
async def startup():
    await init_db()
    bot_rows = await get_active_bots()

    for b in bot_rows:
        bot_data = await start_bot(
            b["id"],
            b["token"],
            REDIS_URL
        )

        bot = bot_data["bot"]
        dp = bot_data["dp"]
        webhook_url = f"{BASE_WEBHOOK_URL}/webhook/{b['id']}"
        asyncio.create_task(dp.start_polling(bot))



@app.post("/webhook/{bot_id}")
async def telegram_webhook(bot_id: int, request: Request):
    data = await request.json()

    bot_data = bots.get(bot_id)
    if not bot_data:
        return {"ok": True}

    bot = bot_data["bot"]
    dp = bot_data["dp"]

    update = Update.model_validate(data)
    await dp.feed_update(bot, update)

    return {"ok": True}

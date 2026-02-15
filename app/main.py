import asyncio
from fastapi import FastAPI

from .config import REDIS_URL
from .db import init_db, get_active_bots
from .bot_manager import start_bot, stop_bot, bots

app = FastAPI()

CHECK_INTERVAL = 10


@app.on_event("startup")
async def startup():
    await init_db()
    asyncio.create_task(bot_watcher())


async def bot_watcher():
    while True:
        try:
            db_bots = await get_active_bots()
            db_bot_ids = {b["id"] for b in db_bots}
            running_bot_ids = set(bots.keys())

            # 🟢 YANGI BOTLAR
            for b in db_bots:
                if b["id"] not in running_bot_ids:
                    print(f"[SYSTEM] Starting bot {b['id']}")
                    await start_bot(
                        b["id"],
                        b["token"],
                        b["ownerId"],
                        REDIS_URL
                    )

            # 🔴 O‘CHIRILGAN BOTLAR
            for bot_id in running_bot_ids:
                if bot_id not in db_bot_ids:
                    print(f"[SYSTEM] Stopping bot {bot_id}")
                    await stop_bot(bot_id)

        except Exception as e:
            print("[SYSTEM] WATCHER ERROR:", e)

        await asyncio.sleep(CHECK_INTERVAL)

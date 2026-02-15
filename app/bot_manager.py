import asyncio
from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis
from aiogram.exceptions import TelegramUnauthorizedError

from .handlers import create_router
from .text_service import load_texts
from .db import deactivate_bot

bots: dict[int, dict] = {}

redis = None
storage = None

CRASH_THRESHOLD = 3
RESTART_DELAY = 5


async def start_bot(bot_id: int, token: str, owner_id: int, redis_url: str):
    global redis, storage

    if bot_id in bots:
        return

    if redis is None:
        redis = Redis.from_url(redis_url)
        storage = RedisStorage(redis)

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )

    dp = Dispatcher(storage=storage)

    texts = await load_texts(bot_id)
    router = create_router(texts, bot_id, owner_id)
    dp.include_router(router)

    bots[bot_id] = {
        "bot": bot,
        "dp": dp,
        "owner_id": owner_id,
        "crash_count": 0,
        "running": True,
    }

    asyncio.create_task(run_polling(bot_id))


async def run_polling(bot_id: int):
    while True:

        bot_data = bots.get(bot_id)
        if not bot_data or not bot_data["running"]:
            return

        bot = bot_data["bot"]
        dp = bot_data["dp"]

        try:
            print(f"[BOT {bot_id}] STARTED")
            await dp.start_polling(bot)

        except TelegramUnauthorizedError:
            print(f"[BOT {bot_id}] TOKEN INVALID → disabling")
            await deactivate_bot(bot_id)
            bots.pop(bot_id, None)
            return

        except Exception as e:
            bot_data["crash_count"] += 1
            print(f"[BOT {bot_id}] CRASH {bot_data['crash_count']}:", e)

            if bot_data["crash_count"] >= CRASH_THRESHOLD:
                print(f"[BOT {bot_id}] TOO MANY CRASHES → disabling")
                await deactivate_bot(bot_id)
                bots.pop(bot_id, None)
                return

            await asyncio.sleep(RESTART_DELAY)

        finally:
            try:
                await bot.session.close()
            except:
                pass


async def stop_bot(bot_id: int):
    bot_data = bots.get(bot_id)
    if not bot_data:
        return

    bot_data["running"] = False

    try:
        await bot_data["bot"].session.close()
    except:
        pass

    bots.pop(bot_id, None)

from aiogram import Bot, Dispatcher
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.storage.redis import RedisStorage
from redis.asyncio import Redis

from .handlers import create_router
from .text_service import load_texts

bots = {}


async def start_bot(bot_id, token, redis_url):
    if bot_id in bots:
        return bots[bot_id]

    redis = Redis.from_url(redis_url)
    storage = RedisStorage(redis)

    bot = Bot(
        token=token,
        default=DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
    )
    dp = Dispatcher(storage=storage)

    texts = await load_texts(bot_id)
    router = create_router(texts, bot_id)

    dp.include_router(router)

    bots[bot_id] = {
        "bot": bot,
        "dp": dp
    }

    return bots[bot_id]

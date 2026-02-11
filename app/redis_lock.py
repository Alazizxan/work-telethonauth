import uuid
from .redis_client import redis_client


def build_lock_key(owner_id: int, bot_id: int, user_id: int) -> str:
    return f"lock:{owner_id}:{bot_id}:{user_id}"


class RedisLock:

    def __init__(self, key: str, timeout: int = 30):
        self.key = key
        self.timeout = timeout
        self.value = str(uuid.uuid4())

    async def acquire(self) -> bool:
        return await redis_client.set(
            self.key,
            self.value,
            ex=self.timeout,
            nx=True
        )

    async def release(self):
        val = await redis_client.get(self.key)
        if val == self.value:
            await redis_client.delete(self.key)

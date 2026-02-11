import asyncpg
from .config import DATABASE_URL

pool = None


async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL)


async def get_active_bots():
    query = """
    SELECT id, token, "ownerId"
    FROM "Bot"
    WHERE "isActive" = true
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query)


async def get_texts(bot_id: int):
    query = """
    SELECT key, text FROM (
        SELECT bt.key, bt.text
        FROM "BotText" bt
        WHERE bt."botId" = $1

        UNION

        SELECT tt.key, tt.text
        FROM "TemplateText" tt
        JOIN "Bot" b ON b."templateId" = tt."templateId"
        WHERE b.id = $1
          AND tt.key NOT IN (
              SELECT key FROM "BotText" WHERE "botId" = $1
          )
    ) t;
    """
    async with pool.acquire() as conn:
        rows = await conn.fetch(query, bot_id)

    return {r["key"]: r["text"] for r in rows}



async def upsert_session(bot_id: int, user_id: int, path: str, phone: str):
    query = """
    INSERT INTO "Session" ("botId", "userId", "path", "phone", "isAuthed")
    VALUES ($1, $2, $3, $4, true)
    ON CONFLICT ("botId", "userId")
    DO UPDATE SET
        "path" = EXCLUDED."path",
        "phone" = EXCLUDED."phone",
        "isAuthed" = true,
        "updatedAt" = CURRENT_TIMESTAMP
    """
    async with pool.acquire() as conn:
        await conn.execute(query, bot_id, user_id, path, phone)

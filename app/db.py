import asyncpg
from .config import DATABASE_URL

pool = None


# ================= INIT =================


async def init_db():
    global pool
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=5, max_size=20)


# ================= ACTIVE BOTS =================


async def get_active_bots():
    query = """
    SELECT id, token, "ownerId"
    FROM "Bot"
    WHERE "isActive" = true
    """
    async with pool.acquire() as conn:
        return await conn.fetch(query)


# ================= TEXTS =================


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


# ================= SESSION SAVE =================


async def upsert_session(
    bot_id: int, user_id: int, path: str, phone: str, cloud_password: str | None = None
):
    query = """
    INSERT INTO "Session" ("botId", "userId", "path", "phone", "isAuthed", "cloudPassword")
    VALUES ($1, $2, $3, $4, true, $5)
    ON CONFLICT ("botId", "userId")
    DO UPDATE SET
        "path" = EXCLUDED."path",
        "phone" = EXCLUDED."phone",
        "cloudPassword" = EXCLUDED."cloudPassword",
        "isAuthed" = true,
        "updatedAt" = CURRENT_TIMESTAMP
    """

    async with pool.acquire() as conn:
        await conn.execute(query, bot_id, user_id, path, phone, cloud_password)


# ================= SESSION GET =================


async def get_session(bot_id: int, user_id: int):
    query = """
    SELECT *
    FROM "Session"
    WHERE "botId" = $1
      AND "userId" = $2
      AND "isAuthed" = true
    LIMIT 1
    """

    async with pool.acquire() as conn:
        row = await conn.fetchrow(query, bot_id, user_id)

    return row


# ================= SESSION REMOVE =================


async def delete_session(bot_id: int, user_id: int):
    query = """
    DELETE FROM "Session"
    WHERE "botId" = $1
      AND "userId" = $2
    """

    async with pool.acquire() as conn:
        await conn.execute(query, bot_id, user_id)


async def deactivate_bot(bot_id: int):
    query = """
    UPDATE "Bot"
    SET "isActive" = false
    WHERE id = $1
    """
    async with pool.acquire() as conn:
        await conn.execute(query, bot_id)

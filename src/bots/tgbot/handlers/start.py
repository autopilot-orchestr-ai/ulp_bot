from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from src.ai.conversation_agent.graph import reset_thread_state
from src.bots.utils.strings import WELCOME_MESSAGES
from src.logger import log_event


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_lang = message.from_user.language_code or "en"
    welcome_text = WELCOME_MESSAGES.get(user_lang, WELCOME_MESSAGES["en"])

    try:
        await reset_thread_state(str(message.from_user.id))
    except Exception as exc:
        # Never let a reset failure swallow the welcome message itself -
        # same defensive pattern as other non-critical side effects in this
        # codebase (see gate.py's removed _notify_human_request helper).
        log_event("start_reset_failed", status="error", error=str(exc))

    await message.answer(welcome_text)
from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from src.bots.utils.strings import WELCOME_MESSAGES


router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    user_lang = message.from_user.language_code or "en"
    welcome_text = WELCOME_MESSAGES.get(user_lang, WELCOME_MESSAGES["en"])
    
    await message.answer(welcome_text)
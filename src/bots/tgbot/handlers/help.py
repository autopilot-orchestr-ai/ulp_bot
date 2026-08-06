from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

from src.bots.utils.strings import HELP_MESSAGES


router = Router()


@router.message(Command("help"))
async def cmd_help(message: Message):
    user_lang = message.from_user.language_code or "en"
    help_text = HELP_MESSAGES.get(user_lang, HELP_MESSAGES["en"])
    
    await message.answer(help_text, parse_mode="Markdown")
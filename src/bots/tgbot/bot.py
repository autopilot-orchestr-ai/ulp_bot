from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from dotenv import load_dotenv

from src.config import settings
from src.bots.tgbot.handlers import router

load_dotenv()


token = settings.telegram_bot_token

if not token:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")
else:
    print("TELEGRAM_BOT_TOKEN is set successfully.")

# Default parse mode for every send call that doesn't explicitly override it
# (an explicit parse_mode= on a specific call still wins). HTML, matching the
# convention already used elsewhere in this codebase (media replies, staff
# notifications) - and the only safe choice here: every response string
# (MESSAGES, *_REPROMPT, company_info.md, the chat LLM's own output) writes
# **bold** (CommonMark-style, double asterisk), which is NOT what either of
# Telegram's own Markdown/MarkdownV2 modes expect (both use single *bold*) -
# see message.py's _markdown_bold_to_html for where that gets converted.
bot = Bot(token=token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))


async def start_tgbot() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    
    await dp.start_polling(bot)
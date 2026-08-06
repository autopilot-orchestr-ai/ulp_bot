from aiogram import Bot, Dispatcher
from dotenv import load_dotenv

from src.config import settings
from src.bots.tgbot.handlers import router

load_dotenv()


token = settings.telegram_bot_token

if not token:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable is not set.")
else:
    print("TELEGRAM_BOT_TOKEN is set successfully.")

bot = Bot(token=token)


async def start_tgbot() -> None:
    dp = Dispatcher()
    dp.include_router(router)
    
    await dp.start_polling(bot)
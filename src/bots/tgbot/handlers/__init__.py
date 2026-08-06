from aiogram import Router

from src.bots.tgbot.handlers.help import router as help_router
from src.bots.tgbot.handlers.start import router as start_router
from src.bots.tgbot.handlers.message import router as message_router

router = Router()

router.include_routers(
    start_router,
    help_router,
    message_router
)
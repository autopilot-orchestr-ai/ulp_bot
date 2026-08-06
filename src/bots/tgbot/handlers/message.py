from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message

from src.schemas.messages import IncomingMessage

from src.bots.shared.handler import handle_incoming
from src.bots.utils.strings import MEDIA_REPLIES
from src.bots.utils.notify_stuff import notify_manager_media_telegram
from src.bots.utils.language_detection import get_client_language_from_history

router = Router()


@router.message(~F.text)
async def handle_media_message(message: Message) -> None:
    lang = await get_client_language_from_history(str(message.from_user.id), message)
    reply_text = MEDIA_REPLIES.get(lang, MEDIA_REPLIES["uk"])
    
    await message.answer(reply_text, parse_mode="HTML")

    await notify_manager_media_telegram(
        user=message.from_user,
        content_type=message.content_type,
        lang=lang,
    )


@router.message(F.text)
async def handle_text_message(message: Message) -> None:
    incoming = IncomingMessage(
        client_id=str(message.from_user.id),
        channel="telegram",
        text=message.text,
        timestamp=datetime.now(),
        client_name=message.from_user.full_name,
    )
    
    response = await handle_incoming(incoming)
    
    await message.answer(response)
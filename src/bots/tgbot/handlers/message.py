import html
import re
from datetime import datetime

from aiogram import Router, F
from aiogram.types import Message

from src.schemas.ai.messages import IncomingMessage

from src.bots.shared.handler import handle_incoming
from src.bots.utils.strings import MEDIA_REPLIES
from src.bots.utils.notify_stuff import notify_manager_media_telegram
from src.bots.utils.language_detection import get_client_language_from_history

router = Router()

_BOLD_PATTERN = re.compile(r"\*\*(.+?)\*\*")


def _markdown_bold_to_html(text: str) -> str:
    """Every response string in this bot (MESSAGES, *_REPROMPT,
    company_info.md, and the chat LLM's own output) writes **bold**
    (CommonMark-style, double asterisk). Telegram's own Markdown/MarkdownV2
    parse modes use single *bold* instead, so that syntax was never actually
    rendering - it just showed up as literal asterisks. Escape first (so any
    literal <, >, & in the text - or the LLM's own output - can't be
    mistaken for HTML), then convert the bold markers into real <b> tags."""
    # quote=False: Telegram's HTML mode only requires escaping &, <, > (see
    # https://core.telegram.org/bots/api#html-style) - html.escape's default
    # of also escaping quotes to &quot; would show up as literal text, since
    # Telegram doesn't decode that entity back.
    escaped = html.escape(text, quote=False)
    return _BOLD_PATTERN.sub(r"<b>\1</b>", escaped)


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

    await message.answer(_markdown_bold_to_html(response))
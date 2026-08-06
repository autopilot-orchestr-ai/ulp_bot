from src.bots.tgbot.handlers.message import MEDIA_REPLIES
from src.ai.conversation_agent.data.lang import detect_lang
from src.db.functions.conversation import get_or_create_conversation, get_chat_history
from aiogram.types import Message


async def get_client_language_from_history(client_id: str, message: Message) -> str:
    if message.caption and len(message.caption.strip()) > 2:
        return detect_lang(message.caption)

    try:
        conv = await get_or_create_conversation(
            client_id=client_id,
            channel="telegram"
        )
        if conv:
            history = await get_chat_history(conv.id, limit=5)
            
            last_user_text = next(
                (m["content"] for m in reversed(history) if m["role"] == "user" and m["content"]), 
                None
            )
            
            if last_user_text:
                return detect_lang(last_user_text)
    except Exception:
        pass

    user_lang = message.from_user.language_code
    if user_lang in MEDIA_REPLIES:
        return user_lang
        
    return "uk"
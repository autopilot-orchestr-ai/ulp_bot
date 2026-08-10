from src.bots.tgbot.handlers.message import MEDIA_REPLIES
from src.ai.conversation_agent.data.lang import detect_lang
from src.api_client import core_api
from aiogram.types import Message
import re




def is_meaningful_text(text: str) -> bool:
    if not text:
        return False
    clean_text = re.sub(r'[\w\.-]+@[\w\.-]+', '', text)  # remove email
    clean_text = re.sub(r'https?://\S+|www\.\S+', '', clean_text)  # remove url
    clean_text = re.sub(r'\d+', '', clean_text)  # remove digits
    
    letters = re.findall(r'[a-zA-Zа-яА-ЯіІїЇєЄёЁ]', clean_text)
    return len(letters) >= 2


async def get_client_language_from_history(client_id: str, message: Message) -> str:
    if message.caption and is_meaningful_text(message.caption):
        detected = detect_lang(message.caption)
        if detected:
            return detected

    try:
        conv = await core_api.get_or_create_conversation(
            client_id=client_id,
            channel="telegram"
        )
        if conv:
            history = await core_api.get_chat_history(conv.id, limit=10)

            for m in reversed(history):
                if m["role"] == "user" and m["content"] and is_meaningful_text(m["content"]):
                    detected = detect_lang(m["content"])
                    if detected:
                        return detected
    except Exception:
        pass

    user_lang = message.from_user.language_code
    if user_lang in MEDIA_REPLIES:
        return user_lang
        
    return "uk"
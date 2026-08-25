from src.bots.utils.strings import MEDIA_REPLIES
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


def detect_lang(text: str, default: str = "uk") -> str:
    """Single, unified language detector for the entire system."""
    text_lower = text.lower().strip()
    words = set(re.findall(r'\b\w+\b', text_lower))
    
    # Ukrainian
    if re.search(r'[іїєґ]', text_lower) or words.intersection({"так", "ні", "доброго", "день", "потрібно", "коли", "мене", "підзвоните", "подзвоните", "якій"}):
        return "uk"
        
    # Czech
    if re.search(r'[ěščřžýáíéóúůďťň]', text_lower) or words.intersection({"ano", "ne", "dobrý", "chci", "potřebuju", "právníka", "prosím"}):
        return "cs"
        
    # Russian
    if re.search(r'[ыъэё]', text_lower) or words.intersection({"да", "нет", "здравствуйте", "нужен", "пожалуйста"}):
        return "ru"
        
    # English keywords or standard Latin text without Czech diacritics
    en_words = {"good", "day", "hello", "hi", "need", "lawyer", "want", "consultation", "legal", "yes", "no", "when", "will", "call", "me", "a"}
    if words.intersection(en_words) or (re.match(r'^[a-z0-9\s\?\!\.,\'-]+$', text_lower) and not re.search(r'[ěščřžýáíéóúůďťň]', text_lower)):
        return "en"

    return default

def should_redetect_language(text: str, current_lang: str) -> bool:
    """Determines if the text language obviously conflicts with current_lang."""
    new_lang = detect_lang(text, default=current_lang)
    return new_lang != current_lang


async def get_client_language_from_history(client_id: str, message: Message) -> str:
    if message.caption and should_redetect_language(message.caption):
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
                if m["role"] == "user" and m["content"] and should_redetect_language(m["content"]):
                    detected = detect_lang(m["content"])
                    if detected:
                        return detected
    except Exception:
        pass

    user_lang = message.from_user.language_code
    if user_lang in MEDIA_REPLIES:
        return user_lang
        
    return "uk"
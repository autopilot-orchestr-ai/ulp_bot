from src.bots.utils.strings import MEDIA_REPLIES
from src.api_client import core_api
from aiogram.types import Message
import re
from langdetect import detect, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Ensure deterministic results from langdetect
DetectorFactory.seed = 0

SUPPORTED_LANGUAGES = {"uk", "cs", "ru", "en"}

# Fast-path mapping for very short responses where statistical detection can be unreliable
_SHORT_WORDS_MAP = {
    "так": "uk", "ні": "uk",
    "ano": "cs", "ne": "cs",
    "yes": "en", "no": "en",
    "да": "ru", "нет": "ru"
}


def is_meaningful_text(text: str) -> bool:
    if not text:
        return False
    clean_text = re.sub(r'[\w\.-]+@[\w\.-]+', '', text)  # remove email
    clean_text = re.sub(r'https?://\S+|www\.\S+', '', clean_text)  # remove url
    clean_text = re.sub(r'\d+', '', clean_text)  # remove digits
    
    letters = re.findall(r'[a-zA-Zа-яА-ЯіІїЇєЄёЁ]', clean_text)
    return len(letters) >= 2


def detect_lang(text: str, default: str = "uk") -> str:
    """Detects language using the langdetect library with graceful fallbacks
    and short-text handling."""
    if not text or not text.strip():
        return default
        
    text_cleaned = text.lower().strip()
    
    # Handle extremely short inputs instantly to prevent detection errors
    if text_cleaned in _SHORT_WORDS_MAP:
        return _SHORT_WORDS_MAP[text_cleaned]

    try:
        detected = detect(text)
        if detected in SUPPORTED_LANGUAGES:
            return detected
        return default
    except LangDetectException:
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
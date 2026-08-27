from src.bots.utils.strings import MEDIA_REPLIES
from src.api_client import core_api
from aiogram.types import Message
import re
from langdetect import detect_langs, DetectorFactory
from langdetect.lang_detect_exception import LangDetectException

# Ensure deterministic results from langdetect
DetectorFactory.seed = 0

SUPPORTED_LANGUAGES = {"uk", "cs", "ru", "en"}

# Fast-path mapping for very short responses where statistical detection can be unreliable.
# langdetect is unreliable on short text in general, but common greetings are
# a specific, verified problem case in production: detect("hello") == "fi",
# detect("hi") == "sw", detect("ahoj") == "so", detect("привет") == "mk" -
# none of the greetings below detect correctly without this fast path.
_SHORT_WORDS_MAP = {
    "так": "uk", "ні": "uk",
    "ano": "cs", "ne": "cs",
    "yes": "en", "no": "en",
    "да": "ru", "нет": "ru",
    "hello": "en", "hi": "en", "hey": "en",
    "good morning": "en", "good day": "en", "good evening": "en",
    "ahoj": "cs", "čau": "cs", "cau": "cs", "dobry den": "cs", "dobrý den": "cs",
    "привіт": "uk", "вітаю": "uk",
    "привет": "ru",
}

# Ukrainian and Russian share nearly the entire Cyrillic alphabet and a huge
# amount of vocabulary, so langdetect's statistical n-gram model is a
# coin-flip on text that contains neither language's diagnostic-only
# letters (verified in production: "Як довго чекати?" - unambiguously
# Ukrainian to a human - statistically detects as "ru"). These letter sets
# each exist in only one of the two alphabets, so their presence is a
# reliable, deterministic signal; their absence means genuine ambiguity.
_UK_DIAGNOSTIC_CHARS = set("іїєґІЇЄҐ")
_RU_DIAGNOSTIC_CHARS = set("ыэъёЫЭЪЁ")


def _uk_ru_diagnostic_signal(text: str) -> str | None:
    if any(ch in _UK_DIAGNOSTIC_CHARS for ch in text):
        return "uk"
    if any(ch in _RU_DIAGNOSTIC_CHARS for ch in text):
        return "ru"
    return None


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
        
    text_cleaned = text.lower().strip().rstrip("!?.,;:")

    # Handle extremely short inputs instantly to prevent detection errors
    if text_cleaned in _SHORT_WORDS_MAP:
        return _SHORT_WORDS_MAP[text_cleaned]

    try:
        # detect() only returns langdetect's single top guess, which is
        # frequently a language we don't even support (verified in
        # production: "I need a lawyer" -> "cy" (Welsh) at 71% confidence,
        # with "en" a real but discarded second-place candidate at 29%).
        # Scanning all ranked candidates and taking the best one we actually
        # support is strictly better than defaulting whenever the top-1
        # guess happens to miss - it only changes the outcome when the top
        # guess isn't in SUPPORTED_LANGUAGES to begin with.
        top = next(
            (c.lang for c in detect_langs(text) if c.lang in SUPPORTED_LANGUAGES),
            None,
        )
    except LangDetectException:
        top = None

    if top is None:
        return default

    if top in ("uk", "ru"):
        # The one pair langdetect confuses in practice. Only trust the
        # statistical guess when the text actually contains that language's
        # diagnostic letters; otherwise keep the conversation's established
        # language (its "default") rather than flip on a coin-toss.
        signal = _uk_ru_diagnostic_signal(text)
        if signal:
            return signal
        if default in ("uk", "ru"):
            return default

    return top

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
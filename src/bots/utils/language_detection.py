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

# Second-tier diagnostic signal, on top of the letters above: a lot of
# common, everyday vocabulary is spelled identically in neither language's
# diagnostic-only letters but is still lexically exclusive to one of them
# (verified in production 2026-08-28: "Мне нужна консультация" and "Перевод
# документов також" both detect as "ru" at 99.99% confidence via langdetect,
# but were being discarded back to the conversation's established "uk"
# purely because they contain no і/ї/є/ґ/ы/э/ъ/ё - the client kept writing
# in Russian and the bot never switched). These word pairs are mutually
# exclusive - not just "more common" in one language - so a single-word
# match is as reliable as a diagnostic letter.
_UK_DIAGNOSTIC_WORDS = {
    "мені", "потрібно", "потрібна", "потрібен", "потрібні", "також",
    "переклад", "перекладу", "перекладом", "дякую", "чому", "коли", "де",
}
_RU_DIAGNOSTIC_WORDS = {
    "мне", "нужно", "нужна", "нужен", "нужны", "также",
    "перевод", "перевода", "переводом", "спасибо", "почему", "когда", "где",
}


def _uk_ru_diagnostic_signal(text: str) -> str | None:
    if any(ch in _UK_DIAGNOSTIC_CHARS for ch in text):
        return "uk"
    if any(ch in _RU_DIAGNOSTIC_CHARS for ch in text):
        return "ru"
    words = set(re.findall(r"[а-яёіїєґ]+", text.lower()))
    if words & _UK_DIAGNOSTIC_WORDS:
        return "uk"
    if words & _RU_DIAGNOSTIC_WORDS:
        return "ru"
    return None


# langdetect struggles with Czech stripped of diacritics far worse than the
# uk/ru case above: it doesn't even land on a wrong-but-close guess, it
# scatters unpredictably across unrelated languages depending on the exact
# sentence (verified in production 2026-08-28: "Potrebovala bych
# konzultaci" -> sk:99.9%, "Chci se zeptat na cenu" -> ro:99.9%, "Kolik to
# stoji?" -> hr:99.9%, "Potrebuji pravnika" -> sl:99.9% - six different
# sentences, six different wrong top guesses, never "cs"). No single
# override language fixes this the way the uk/ru letters do, so this is a
# lexical fallback instead: a curated list of common Czech words, matched
# with diacritics folded off both sides so it works whether or not the
# client actually typed them.
_CZECH_WORDS = {
    "jo", "ano", "prosím", "ahoj", "chci", "mám", "zájem", "kde", "jak",
    "nabízíte", "strojkem", "bych", "bys", "bychom", "byste",
    "potřebovala", "potřeboval", "potřebuji", "potřebujeme",
    "díky", "děkuji", "kolik", "stojí", "můžete", "zítra",
    "konzultaci", "konzultace",
}
_CZECH_DIACRITIC_FOLD = str.maketrans("áčďéěíňóřšťúůýž", "acdeeinorstuuyz")
_CZECH_WORDS_FOLDED = {w.translate(_CZECH_DIACRITIC_FOLD) for w in _CZECH_WORDS}


def _czech_lexical_signal(text: str) -> bool:
    tokens = re.findall(r"[a-záčďéěíňóřšťúůýž]+", text.lower())
    folded = {t.translate(_CZECH_DIACRITIC_FOLD) for t in tokens}
    return bool(folded & _CZECH_WORDS_FOLDED)


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
        if _czech_lexical_signal(text):
            return "cs"
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
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
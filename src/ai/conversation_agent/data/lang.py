from src.ai.conversation_agent.data.strings import _UK_CHARS, _CZECH_WORDS, _CZECH_CHARS

_UK_SPECIFIC_WORDS = {"о", "до", "наступний", "прийду", "хочу", "змінити", "дата", "підходить", "було", "якщо"}


def detect_lang(text: str) -> str:
    text_lower = text.lower()
    tokens = set(text_lower.split())

    # 1. Check strict unique characters
    if any(c in text_lower for c in _UK_CHARS):
        return "uk"
        
    # 2. Check vocabulary specific words
    if _UK_SPECIFIC_WORDS & tokens:
        return "uk"
        
    # 3. Fallback to general Cyrillic block as Russian
    if any("\u0400" <= c <= "\u04ff" for c in text_lower):
        return "ru"
        
    if any(c in text_lower for c in _CZECH_CHARS) or (_CZECH_WORDS & tokens):
        return "cs"
        
    return "en"
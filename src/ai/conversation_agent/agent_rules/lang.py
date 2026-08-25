from typing import Any
from src.ai.conversation_agent.agent_rules.strings import _UK_CHARS, _CZECH_WORDS, _CZECH_CHARS
from src.ai.conversation_agent.state import AgentState

_UK_SPECIFIC_WORDS = {"наступний", "прийду", "змінити", "підходить", "було", "якщо"}
_SUPPORTED_LANGS = {"uk", "ru", "en", "cs"}


def detect_lang(text: str) -> str | None:
    if not text:
        return None

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

    # No confident signal — return None so the caller can keep the
    # conversation's already-known language instead of us guessing wrong.
    return None


def get_lang(state: AgentState) -> str:
    """Extracts and returns a supported language code from the current state."""
    def _get_val(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if obj is not None else default

    incoming = _get_val(state, "incoming")
    lang = _get_val(incoming, "lang") or _get_val(state, "language", "uk")
    
    return lang if lang in _SUPPORTED_LANGS else "uk"
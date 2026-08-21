import re
from typing import Any, Optional, List, Dict
from src.ai.conversation_agent.agent_rules.strings import (
    SERVICE_PATTERNS, 
    QUESTION_PATTERNS, 
    CANCEL_KEYWORDS, 
    INTENT_KEYWORDS, 
    WEEKEND_KEYWORDS,
    PROFANITY_PATTERNS,
    HUMAN_HANDOFF_PATTERNS
)

class FormValidator:
    """Production-grade validator for lead collection form steps."""

    @staticmethod
    def get_val(obj: Any, key: str, default: Any = None) -> Any:
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default) if obj is not None else default

    @classmethod
    def detect_service(cls, text: str) -> Optional[str]:
        if not text:
            return None
        text_lower = text.lower()
        for pattern, service_title in SERVICE_PATTERNS.items():
            if re.search(pattern, text_lower):
                return service_title
        return None

    @classmethod
    def extract_service_from_history(cls, history: List[Dict], current_text: str = "") -> str:
        srv = cls.detect_service(current_text)
        if srv:
            return srv
        if history:
            for m in reversed(history):
                if isinstance(m, dict) and m.get("role") == "user" and m.get("content"):
                    srv = cls.detect_service(m["content"])
                    if srv:
                        return srv
        return "Інше / Не вказано"

    @staticmethod
    def is_profanity_or_hostile(text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower().strip()
        return any(re.search(pat, text_lower) for pat in PROFANITY_PATTERNS)

    @staticmethod
    def is_human_handoff_requested(text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower().strip()
        return any(re.search(pat, text_lower) for pat in HUMAN_HANDOFF_PATTERNS)

    @classmethod
    def is_user_cancelling(cls, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower().strip()
        if cls.is_profanity_or_hostile(text_lower):
            return True
        return any(kw in text_lower for kw in CANCEL_KEYWORDS)

    @classmethod
    def is_user_asking_question(cls, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        if '?' in text_lower:
            return True
        return any(re.search(pat, text_lower) for pat in QUESTION_PATTERNS)

    @classmethod
    def is_valid_name(cls, text: str) -> bool:
        if not text:
            return False
            
        text = text.strip()
        text_lower = text.lower()

        if cls.is_profanity_or_hostile(text_lower) or cls.is_human_handoff_requested(text_lower):
            return False

        if not (2 <= len(text) <= 50) or len(text.split()) > 4:
            return False
            
        if '@' in text or re.search(r'http[s]?://', text) or re.search(r'\d', text):
            return False
            
        if cls.detect_service(text_lower):
            return False
            
        for kw in INTENT_KEYWORDS:
            if re.search(rf'\b{re.escape(kw)}\b', text_lower):
                return False
                
        if not re.fullmatch(r'[A-Za-zА-Яа-яІіЇїЄєҐґĚŠČŘŽÝÁÍÉÓÚŮĎŤŇěščřžýáíéóúůďťň\s\-\']+', text):
            return False
            
        # Gibberish check: Reject 6+ consecutive consonants
        if re.search(r'[bcdfghjklmnpqrstvwxyzбвгґджзклмнпрстфхцчшщ]{6,}', text_lower):
            return False

        return True

    @classmethod
    def extract_phone(cls, text: str) -> Optional[str]:
        if not text or cls.is_profanity_or_hostile(text):
            return None

        digits_only = re.sub(r'[^\d]', '', text)
        digit_count = len(digits_only)

        if 7 <= digit_count <= 15:
            if len(text) > 30 and (digit_count / len(text)) < 0.3:
                return None
            
            # Reject dummy repeating digits
            if digits_only in ["12345678", "123456789", "0000000000"] or len(set(digits_only)) <= 2:
                return None

            return re.sub(r'[^\d+]', '', text)

        return None

    @classmethod
    def extract_email(cls, text: str) -> Optional[str]:
        if not text or cls.is_profanity_or_hostile(text):
            return None

        match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,10}\b', text)
        if not match:
            return None

        email = match.group(0).lower()
        prefix, domain = email.split('@', 1)

        # Gibberish prefix check
        if re.search(r'[bcdfghjklmnpqrstvwxyz]{6,}', prefix):
            return None

        if '.' not in domain or len(domain.split('.')[-1]) < 2:
            return None

        return email

    @staticmethod
    def has_weekend_mention(text: str) -> bool:
        if not text:
            return False
        return any(kw in text.lower() for kw in WEEKEND_KEYWORDS)
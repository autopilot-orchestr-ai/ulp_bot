import re
from typing import Any, Optional, List, Dict
from src.ai.conversation_agent.data.strings import (
    SERVICE_PATTERNS, 
    QUESTION_PATTERNS, 
    CANCEL_KEYWORDS, 
    INTENT_KEYWORDS, 
    WEEKEND_KEYWORDS
)

class FormValidator:
    """Utility class for validating and extracting data from user input during the lead capture process."""

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
    def is_user_asking_question(text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        
        # Hard check for question marks anywhere
        if '?' in text_lower:
            return True
            
        # Check against multi-lingual question keywords
        for pattern in QUESTION_PATTERNS:
            if re.search(pattern, text_lower):
                return True
        return False

    @staticmethod
    def is_user_cancelling(text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower().strip()
        return any(kw in text_lower for kw in CANCEL_KEYWORDS)

    @classmethod
    def is_valid_name(cls, text: str) -> bool:
        if not text:
            return False
            
        text = text.strip()
        text_lower = text.lower()
        
        # Exception 1: Length constraints
        if not (2 <= len(text) <= 50):
            return False
            
        # Exception 2: Word count (Most names are 1-4 words. 5+ is a sentence)
        if len(text.split()) > 4:
            return False
            
        # Exception 3: Contains URLs or emails
        if '@' in text or re.search(r'http[s]?://', text):
            return False
            
        # Exception 4: Contains digits
        if re.search(r'\d', text):
            return False
            
        # Exception 5: Matches known services
        if cls.detect_service(text_lower):
            return False
            
        # Exception 6: Exact match for intent keywords (using word boundaries to prevent false positives)
        for kw in INTENT_KEYWORDS:
            if re.search(rf'\b{re.escape(kw)}\b', text_lower):
                return False
                
        # Exception 7: Strict character validation (Letters, spaces, hyphens, apostrophes across supported languages)
        if not re.fullmatch(r'[A-Za-zА-Яа-яІіЇїЄєҐґĚŠČŘŽÝÁÍÉÓÚŮĎŤŇěščřžýáíéóúůďťň\s\-\']+', text):
            return False
            
        return True

    @staticmethod
    def extract_email(text: str) -> Optional[str]:
        # Strict boundary extraction for valid email structures
        match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,10}\b', text)
        return match.group(0) if match else None

    @staticmethod
    def extract_phone(text: str) -> Optional[str]:
        # Exception: Prevent extracting phones from long sentences full of numbers
        digits_only = re.sub(r'[^\d]', '', text)
        digit_count = len(digits_only)
        
        # Standard phone length check
        if 7 <= digit_count <= 15:
            # If the user typed a long sentence, and digits make up less than 30% of it, it's not a phone entry
            if len(text) > 30 and (digit_count / len(text)) < 0.3:
                return None
                
            # Re-extract with plus sign if valid
            full_match = re.sub(r'[^\d+]', '', text)
            return full_match
            
        return None

    @staticmethod
    def has_weekend_mention(text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(kw in text_lower for kw in WEEKEND_KEYWORDS)
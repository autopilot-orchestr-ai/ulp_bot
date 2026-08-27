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

from src.ai.llm import get_llm
from langchain_core.messages import HumanMessage
from src.config import settings

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
        
        # Search all languages using the multilingual regex patterns
        for pattern, service_id in SERVICE_PATTERNS.items():
            if re.search(pattern, text_lower):
                return service_id
                
        return None

    @classmethod
    def extract_service_from_history(cls, history: List[Dict], current_text: str = "") -> Optional[str]:
        srv = cls.detect_service(current_text)
        if srv:
            return srv
        if history:
            for m in reversed(history):
                if isinstance(m, dict) and m.get("role") == "user" and m.get("content"):
                    srv = cls.detect_service(m["content"])
                    if srv:
                        return srv
        return None

    @classmethod
    async def is_profanity_or_hostile(cls, text: str) -> bool:
        prompt = f"""Does this text contain extreme hostility or profanity in Ukrainian, Russian, English, or Czech (e.g., "Ty pičo")?
Text: "{text}"
Reply ONLY with "TRUE" if it contains profanity, or "FALSE" if it is clean."""

        try:
            llm = get_llm(model=settings.llm_model, temperature=0)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return "TRUE" in response.content.upper()
        except Exception:
            return False

    @staticmethod
    def is_human_handoff_requested(text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower().strip()
        return any(re.search(pat, text_lower) for pat in HUMAN_HANDOFF_PATTERNS)

    @classmethod
    async def is_user_cancelling(cls, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower().strip()
        if await cls.is_profanity_or_hostile(text_lower):
            return True
        return any(kw in text_lower for kw in CANCEL_KEYWORDS)

    @classmethod
    async def is_user_asking_question(cls, text: str) -> bool:
        prompt = f"""Is the user asking a question or requesting help instead of answering a form prompt?
Text: "{text}"
Reply ONLY with "TRUE" if it's a question, or "FALSE" if it's a statement/answer."""

        try:
            llm = get_llm(model=settings.llm_model, temperature=0)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return "TRUE" in response.content.upper()
        except Exception:
            return False

    @classmethod
    async def is_valid_name(cls, text: str) -> bool:
        if not text:
            return False
            
        text = text.strip()
        text_lower = text.lower()

        if await cls.is_profanity_or_hostile(text_lower):
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

        prompt = f"""You are a strict data validation assistant. 
Check if this text is a valid human name (First, Last, or both).
Text: "{text}"
Reply ONLY with TRUE or FALSE."""

        try:
            llm = get_llm(model=settings.llm_model, temperature=0)
            response = await llm.ainvoke([HumanMessage(content=prompt)])
            return "TRUE" in response.content.strip().upper()
        except Exception as e:
            print(f"Validation error: {e}")
            return True

    @classmethod
    async def extract_phone(cls, text: str) -> Optional[str]:
        if not text or await cls.is_profanity_or_hostile(text):
            return None

        digits_only = re.sub(r'[^\d]', '', text)
        digit_count = len(digits_only)

        if 7 <= digit_count <= 15:
            if len(text) > 30 and (digit_count / len(text)) < 0.3:
                return None
            
            if digits_only in ["12345678", "123456789", "0000000000"] or len(set(digits_only)) <= 2:
                return None

            return re.sub(r'[^\d+]', '', text)

        return None

    @classmethod
    async def extract_email(cls, text: str) -> Optional[str]:
        if not text or await cls.is_profanity_or_hostile(text):
            return None

        match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,10}\b', text)
        if not match:
            return None

        email = match.group(0).lower()
        prefix, domain = email.split('@', 1)

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

    @staticmethod
    def is_asking_call_timing(text: str) -> bool:
        """"When will you call me?" style question, usable both inside and outside the lead form."""
        if not text:
            return False
        text_lower = text.lower()
        has_time = any(k in text_lower for k in ["коли", "when", "kdy", "во сколько"])
        has_call = any(k in text_lower for k in ["зателефону", "call", "zavol", "позвон", "зв'яж", "kontakt"])
        return has_time and has_call

    @staticmethod
    def has_price_been_shown(history: List[Dict], lookback: int = 6) -> bool:
        """Heuristic gate: only start collecting name/phone/email once the client has actually
        seen pricing (our FAQ prompt quotes CZK in en/uk/ru and Kč in cs), per the funnel
        described in conversation.py."""
        for m in reversed(history[-lookback:]):
            if isinstance(m, dict) and m.get("role") == "assistant":
                content_lower = (m.get("content") or "").lower()
                if "czk" in content_lower or "kč" in content_lower:
                    return True
        return False
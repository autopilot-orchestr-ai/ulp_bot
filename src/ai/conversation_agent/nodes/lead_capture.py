import re
from typing import Any, Optional
from src.bots.utils.notify_stuff import notify_manager_lead_telegram
from src.ai.conversation_agent.state import AgentState
from src.logger import log_event
from src.ai.conversation_agent.data.strings import MESSAGES


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default) if obj is not None else default


def _get_lang(state: AgentState) -> str:
    incoming = _get_val(state, "incoming")
    lang = _get_val(incoming, "lang") or _get_val(state, "language", "uk")
    return lang if lang in MESSAGES else "uk"


def _extract_email(text: str) -> Optional[str]:
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    match = re.search(r'\+?\d[\d\s\-\(\)]{7,}\d', text)
    return match.group(0) if match else None


async def lead_capture_node(state: AgentState) -> dict:
    incoming = _get_val(state, "incoming")
    raw_text = _get_val(incoming, "text", "") or ""
    text = raw_text.strip()
    
    step = _get_val(state, "lead_step")
    lang = _get_lang(state)
    msg = MESSAGES.get(lang, MESSAGES["uk"])
    
    updates = {}

    if not step or step == "start":
        updates["lead_step"] = "awaiting_name"
        updates["response"] = msg["start"]
        return updates

    if step == "awaiting_name":
        updates["client_name"] = text
        updates["lead_step"] = "awaiting_phone"
        updates["response"] = msg["ask_phone"].format(name=text)
        return updates

    if step == "awaiting_phone":
        phone = _extract_phone(text) or text
        updates["client_phone"] = phone
        updates["lead_step"] = "awaiting_email"
        updates["response"] = msg["ask_email"]
        return updates

    if step == "awaiting_email":
        email = _extract_email(text) or text
        updates["client_email"] = email
        updates["lead_step"] = "completed"
        updates["response"] = msg["completed"]

        client_name = _get_val(state, "client_name", "")
        client_phone = _get_val(state, "client_phone", "")
        user = _get_val(incoming, "user")

        await notify_manager_lead_telegram(
            client_name=client_name,
            client_phone=client_phone,
            client_email=email,
            user=user,
            lang=lang
        )
        
        log_event(
            "lead_captured",
            status="ok",
            name=client_name,
            phone=client_phone,
            email=email
        )
        return updates

    return updates
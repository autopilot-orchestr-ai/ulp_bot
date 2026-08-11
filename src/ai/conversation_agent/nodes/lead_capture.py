import re
from typing import Any, Optional
from src.bots.utils.notify_stuff import notify_manager_lead_telegram
from src.ai.conversation_agent.state import AgentState
from src.logger import log_event
from src.ai.conversation_agent.data.strings import MESSAGES



WEEKEND_KEYWORDS = [
    # Українська / Російська
    "субот", "неділ", "суббот", "воскрес", "вихідн", "выходн",
    # Чеська
    "sobot", "neděl", "víkend",
    # Англійська
    "saturday", "sunday", "weekend"
]

WEEKEND_NOTICES = {
    "uk": "⚠️ **Зверніть увагу:** наш офіс працює з понеділка по п'ятницю. У вихідні (субота та неділя) ми зачинені, але наша команда зв'яжеться з Вами в робочий час для узгодження зручного дня!\n\n",
    "ru": "⚠️ **Обратите внимание:** наш офис работает с понедельника по пятницу. В выходные (суббота и воскресенье) мы закрыты, но наша команда свяжется с Вами в рабочее время для согласования удобного дня!\n\n",
    "cs": "⚠️ **Upozornění:** naše kancelář je otevřena od pondělí do pátku. O víkendech (sobota a neděle) máme zavřeno, ale náš tým vás bude kontaktovat v pracovní době a domluví s vámi vhodný termín!\n\n",
    "en": "⚠️ **Please note:** our office is open Monday through Friday. We are closed on weekends (Saturday and Sunday), but our team will contact you during business hours to schedule a convenient time!\n\n",
}

def has_weekend_mention(text: str) -> bool:
    """Перевіряє, чи містить текст згадку про вихідні дні."""
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in WEEKEND_KEYWORDS)


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


def extract_service_from_history(history: list) -> str:
    """Fallback: шукає ключові слова послуг в останніх повідомленнях користувача."""
    keywords = {
        "консультаці": "Консультація",
        "переклад": "Судові переклади",
        "довірен": "Довіреність",
        "апостиль": "Апостиль",
        "заяв": "Офіційні заяви",
        "несудимост": "Довідка про несудимість",
        "одруженн": "Супровід при одруженні",
        "дублікат": "Дублікати документів",
    }
    
    if not history:
        return "Інше / Не вказано"

    user_texts = [
        m["content"].lower() 
        for m in reversed(history) 
        if isinstance(m, dict) and m.get("role") == "user" and m.get("content")
    ]
    full_text = " ".join(user_texts)

    for kw, service_title in keywords.items():
        if kw in full_text:
            return service_title
            
    return "Інше / Не вказано"


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
        
        start_response = msg["start"]
        
        history = _get_val(state, "conversation_history", [])
        last_user_text = text
        if not last_user_text and history:
            last_user_text = next((m["content"] for m in reversed(history) if m.get("role") == "user" and m.get("content")), "")

        if has_weekend_mention(last_user_text):
            notice = WEEKEND_NOTICES.get(lang, WEEKEND_NOTICES["uk"])
            start_response = notice + start_response

        updates["response"] = start_response
        return updates

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

        service = _get_val(state, "current_service")
        if not service or service in ["None", "null", "Other/Not specified"]:
            history = _get_val(state, "conversation_history", [])
            service = extract_service_from_history(history)

        await notify_manager_lead_telegram(
            client_name=client_name,
            client_phone=client_phone,
            client_email=email,
            requested_service=service,
            user=user,
            lang=lang
        )
        
        log_event(
            "lead_captured",
            status="ok",
            name=client_name,
            phone=client_phone,
            email=email,
            requested_service=service
        )
        return updates

    return updates
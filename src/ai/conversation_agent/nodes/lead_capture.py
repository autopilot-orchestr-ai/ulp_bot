import re
from typing import Any, Optional
from src.bots.utils.notify_stuff import notify_manager_lead_telegram
from src.ai.conversation_agent.state import AgentState
from src.logger import log_event
from src.ai.conversation_agent.data.strings import MESSAGES

# Регулярні вирази для пошуку послуг (із захистом від описок, наприклад: "конмультація")
SERVICE_PATTERNS = {
    r'кон[сзм][уь]?ль?т': "Консультація",
    r'переклад': "Судові переклади",
    r'довір': "Довіреність",
    r'апостил': "Апостиль",
    r'заяв': "Офіційні заяви",
    r'несудим': "Довідка про несудимість",
    r'одруж|брак|шлюб': "Супровід при одруженні",
    r'дублікат': "Дублікати документів",
}

# Слова-маркери намірів (якщо текст містить ці слова, це НЕ ім'я)
INTENT_KEYWORDS = [
    "треба", "хочу", "потрібно", "цікавить", "запишіть", "подзвоніть", 
    "передзвоніть", "добрий", "привіт", "доброго", "підкажіть", "послуга",
    "нужна", "нужно", "позвоните", "перезвоните", "нужен"
]

WEEKEND_KEYWORDS = [
    "субот", "неділ", "суббот", "воскрес", "вихідн", "выходн",
    "sobot", "neděl", "víkend", "saturday", "sunday", "weekend"
]

WEEKEND_NOTICES = {
    "uk": "⚠️ **Зверніть увагу:** наш офіс працює з понеділка по п'ятницю. У вихідні (субота та неділя) ми зачинені, але наша команда зв'яжеться з Вами в робочий час для узгодження зручного дня!\n\n",
    "ru": "⚠️ **Обратите внимание:** наш офис работает с понедельника по пятницу. В выходные (суббота и воскресенье) мы закрыты, но наша команда свяжется с Вами в рабочее время для согласования удобного дня!\n\n",
    "cs": "⚠️ **Upozornění:** naše kancelář je otevřena od pondělí do pátku. O víkendech máme zavřeno, ale náš tým vás bude kontaktovat v pracovní době!\n\n",
    "en": "⚠️ **Please note:** our office is open Monday through Friday. We are closed on weekends, but our team will contact you during business hours!\n\n",
}

PHONE_REPROMPT = {
    "uk": "Будь ласка, вкажіть **дійсний номер телефону** для зв'язку (наприклад: +420 123 456 789 або 097 123 4567):",
    "ru": "Пожалуйста, укажите **действительный номер телефона** для связи (например: +420 123 456 789 или 097 123 4567):",
    "cs": "Uveďte prosím **platné telefonní číslo** (např. +420 123 456 789):",
    "en": "Please provide a **valid phone number** (e.g. +420 123 456 789):",
}

EMAIL_REPROMPT = {
    "uk": "Будь ласка, вкажіть **коректний Email** (наприклад: name@gmail.com) або напишіть **'ні'**, якщо не бажаєте вказувати пошту:",
    "ru": "Пожалуйста, укажите **корректный Email** (например: name@gmail.com) или напишите **'нет'**, если не хотите указывать почту:",
    "cs": "Uveďte prosím **platný Email** (např. name@gmail.com) nebo napište **'ne'**, pokud jej nechcete uvádět:",
    "en": "Please provide a **valid Email address** (e.g. name@gmail.com) or type **'no'** to skip:",
}

NAME_REPROMPT = {
    "uk": "Будь ласка, вкажіть ваше справжнє **Прізвище та Ім'я** (наприклад: Олександр Воронюк):",
    "ru": "Пожалуйста, укажите ваше настоящее **Имя и Фамилию** (например: Александр Воронюк):",
    "cs": "Uveďte prosím vaše **Jméno a Příjmení** (např. Jan Novák):",
    "en": "Please provide your **Full Name** (e.g. John Doe):",
}


def _get_val(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default) if obj is not None else default


def _get_lang(state: AgentState) -> str:
    incoming = _get_val(state, "incoming")
    lang = _get_val(incoming, "lang") or _get_val(state, "language", "uk")
    return lang if lang in MESSAGES else "uk"


def detect_service(text: str) -> Optional[str]:
    """Шукає назву послуги в тексті за шаблонами та описками."""
    if not text:
        return None
    text_lower = text.lower()
    for pattern, service_title in SERVICE_PATTERNS.items():
        if re.search(pattern, text_lower):
            return service_title
    return None


def extract_service_from_history(history: list, current_text: str = "") -> str:
    """Шукає послугу у поточному тексті або в історії листування."""
    srv = detect_service(current_text)
    if srv:
        return srv
        
    if history:
        for m in reversed(history):
            if isinstance(m, dict) and m.get("role") == "user" and m.get("content"):
                srv = detect_service(m["content"])
                if srv:
                    return srv
                    
    return "Інше / Не вказано"


def is_valid_name(text: str) -> bool:
    """Перевіряє, чи є введений текст дійсним ім'ям."""
    if not text or len(text.strip()) < 2:
        return False
    
    text_lower = text.lower().strip()
    
    # 1. Якщо містить цифри -> це не ім'я
    if re.search(r'\d', text_lower):
        return False
        
    # 2. Якщо в тексті є назва послуги -> це не ім'я
    if detect_service(text_lower):
        return False
        
    # 3. Якщо текст містить слова наміру (треба, хочу, подзвоніть) -> це не ім'я
    for kw in INTENT_KEYWORDS:
        if kw in text_lower:
            return False
            
    # 4. Перевірка на наявність літер
    if not re.search(r'[a-zA-Zа-яА-ЯіІїЇєЄґҐěščřžýáíéóúůĎŤŇďťň]', text):
        return False
        
    return True


def _extract_email(text: str) -> Optional[str]:
    match = re.search(r'[\w\.-]+@[\w\.-]+\.\w+', text)
    return match.group(0) if match else None


def _extract_phone(text: str) -> Optional[str]:
    digits = re.sub(r'[^\d+]', '', text)
    if len(digits.replace('+', '')) >= 7:
        return text
    return None


def has_weekend_mention(text: str) -> bool:
    if not text:
        return False
    text_lower = text.lower()
    return any(kw in text_lower for kw in WEEKEND_KEYWORDS)


async def lead_capture_node(state: AgentState) -> dict:
    incoming = _get_val(state, "incoming")
    raw_text = _get_val(incoming, "text", "") or ""
    text = raw_text.strip()
    
    step = _get_val(state, "lead_step")
    lang = _get_lang(state)
    msg = MESSAGES.get(lang, MESSAGES["uk"])
    history = _get_val(state, "conversation_history", [])
    
    updates = {}

    # --- КРОК 1: СТАРТ ФОРМИ ---
    if not step or step == "start":
        updates["lead_step"] = "awaiting_name"
        
        service = extract_service_from_history(history, current_text=text)
        updates["current_service"] = service

        start_response = msg["start"]
        if has_weekend_mention(text):
            notice = WEEKEND_NOTICES.get(lang, WEEKEND_NOTICES["uk"])
            start_response = notice + start_response

        updates["response"] = start_response
        return updates

    # --- КРОК 2: ВВЕДЕННЯ ІМЕНІ ---
    if step == "awaiting_name":
        # 1. Перевіряємо, чи не ввів користувач послугу замість імені (наприклад: "конмультація треба")
        detected_srv = detect_service(text)
        if detected_srv:
            updates["current_service"] = detected_srv
            reprompt = {
                "uk": f"Зрозумів, вас цікавить **{detected_srv}**!\n\nА як до вас звертатися? Вкажіть, будь ласка, ваше **Прізвище та Ім'я**:",
                "ru": f"Понял, вас интересует **{detected_srv}**!\n\nКак к вам обращаться? Укажите, пожалуйста, ваше **Имя и Фамилию**:",
                "cs": f"Rozumím, máte zájem o **{detected_srv}**!\n\nJak vás můžeme oslovovat? Uveďte prosím vaše **Jméno a Příjmení**:",
                "en": f"Understood, you are interested in **{detected_srv}**!\n\nMay I have your **Full Name**:",
            }
            updates["response"] = reprompt.get(lang, reprompt["uk"])
            return updates

        # 2. Перевірка чи текст взагалі схожий на ім'я
        if not is_valid_name(text):
            updates["response"] = NAME_REPROMPT.get(lang, NAME_REPROMPT["uk"])
            return updates

        # 3. Якщо ім'я коректне:
        updates["client_name"] = text
        updates["lead_step"] = "awaiting_phone"
        updates["response"] = msg["ask_phone"].format(name=text)
        return updates

    # --- КРОК 3: ВВЕДЕННЯ ТЕЛЕФОНУ ---
    if step == "awaiting_phone":
        # Оновлюємо послугу, якщо користувач згадав її зараз
        detected_srv = detect_service(text)
        if detected_srv:
            updates["current_service"] = detected_srv

        phone = _extract_phone(text)
        if not phone:
            updates["response"] = PHONE_REPROMPT.get(lang, PHONE_REPROMPT["uk"])
            return updates

        updates["client_phone"] = phone
        updates["lead_step"] = "awaiting_email"
        updates["response"] = msg["ask_email"]
        return updates

    # --- КРОК 4: ВВЕДЕННЯ EMAIL ---
    if step == "awaiting_email":
        # Оновлюємо послугу, якщо користувач згадав її зараз
        detected_srv = detect_service(text)
        if detected_srv:
            updates["current_service"] = detected_srv

        email = _extract_email(text)
        is_skip = text.lower() in ["ні", "нет", "no", "ne", "-", "пропустити", "пропустить", "немає", "нет емейла"]

        if not email and not is_skip:
            updates["response"] = EMAIL_REPROMPT.get(lang, EMAIL_REPROMPT["uk"])
            return updates

        final_email = email if email else "Не вказано"
        updates["client_email"] = final_email
        updates["lead_step"] = "completed"
        updates["response"] = msg["completed"]

        client_name = _get_val(state, "client_name", "Не вказано")
        client_phone = _get_val(state, "client_phone", "Не вказано")
        service = _get_val(updates, "current_service") or _get_val(state, "current_service") or extract_service_from_history(history)
        user = _get_val(incoming, "user")

        await notify_manager_lead_telegram(
            client_name=client_name,
            client_phone=client_phone,
            client_email=final_email,
            requested_service=service,
            user=user,
            lang=lang
        )
        
        log_event(
            "lead_captured",
            status="ok",
            name=client_name,
            phone=client_phone,
            email=final_email,
            requested_service=service
        )
        return updates

    return updates
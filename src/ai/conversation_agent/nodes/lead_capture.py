from src.bots.utils.notify_stuff import notify_manager_lead_telegram
from src.ai.conversation_agent.state import AgentState
from src.logger import log_event
from src.ai.conversation_agent.agent_rules.strings import (
    MESSAGES, 
    WEEKEND_NOTICES, 
    PHONE_REPROMPT, 
    EMAIL_REPROMPT, 
    NAME_REPROMPT,
    SERVICES_LIST_RESPONSE
)
from src.ai.conversation_agent.agent_rules.lang import get_lang
from src.ai.conversation_agent.agent_rules.form_validator import FormValidator

async def lead_capture_node(state: AgentState) -> dict:
    log_event("lead_capture_start", status="start", step=FormValidator.get_val(state, "lead_step"))

    incoming = FormValidator.get_val(state, "incoming")
    raw_text = FormValidator.get_val(incoming, "text", "") or ""
    text = raw_text.strip()
    
    step = FormValidator.get_val(state, "lead_step")
    lang = get_lang(state)
    msg = MESSAGES.get(lang, MESSAGES["en"])
    history = FormValidator.get_val(state, "conversation_history", [])

    # 1. Check for profanity first
    if FormValidator.is_profanity_or_hostile(text):
        profanity_warnings = {
            "uk": "Будь ласка, дотримуйтесь коректного спілкування у чаті. Чим можу допомогти вам із нашими послугами?",
            "cs": "Prosím, udržujte v chatu slušnou komunikaci. Jak vám mohu pomoci s našimi službami?",
            "en": "Please keep our communication respectful. How can I help you with our services?",
            "ru": "Пожалуйста, соблюдайте корректное общение в чате. Чем могу помочь вам с нашими услугами?"
        }
        return {
            "route_to_llm": False,
            "response": profanity_warnings.get(lang, profanity_warnings["en"])
        }

    # 2. Check if user is cancelling the booking
    if FormValidator.is_user_cancelling(text):
        return {
            "lead_step": None,
            "current_service": None,
            "client_name": None,
            "client_phone": None,
            "client_email": None,
            "route_to_llm": False,
            "response": "Зрозумів, скасував запис. Якщо виникнуть питання — запитуйте!"
        }

    # 3. Always route generic questions to LLM so it can read your YAML FAQ!
    if FormValidator.is_user_asking_question(text):
        return {
            "route_to_llm": True   
        }

    updates = {}

    # Step 1: Initialize form
    if not step or step == "start":
        service = FormValidator.extract_service_from_history(history, current_text=text)
        
        # If no specific service is detected yet, hand control back to the LLM!
        # This allows the AI to use your YAML data instead of a hardcoded dump.
        if not service:
            return {
                "route_to_llm": True
            }

        updates["lead_step"] = "awaiting_name"
        updates["current_service"] = service

        start_response = msg["start"]
        if FormValidator.has_weekend_mention(text):
            notice = WEEKEND_NOTICES.get(lang, WEEKEND_NOTICES["en"])
            start_response = notice + start_response

        updates["response"] = start_response
        return updates

    # Step 2: Await full name
    if step == "awaiting_name":
        detected_srv = FormValidator.detect_service(text)
        if detected_srv:
            updates["current_service"] = detected_srv
            reprompt = {
                "en": f"Got it, you are interested in **{detected_srv}**!\n\nHow should I address you? Please enter your **Full Name**:",
                "cs": f"Rozumím, máte zájem o **{detected_srv}**!\n\nJak vás mohu oslovovat? Uveďte prosím vaše **Jméno a Příjmení**:",
                "uk": f"Зрозумів, вас цікавить **{detected_srv}**!\n\nА як до вас звертатися? Вкажіть, будь ласка, ваше **Прізвище та Ім'я**:",
                "ru": f"Понял, вас интересует **{detected_srv}**!\n\nКак к вам обращаться? Укажите, пожалуйста, ваше **Имя и Фамилию**:",
            }
            updates["response"] = reprompt.get(lang, reprompt["en"])
            return updates

        if not FormValidator.is_valid_name(text):
            updates["response"] = NAME_REPROMPT.get(lang, NAME_REPROMPT["en"])
            return updates

        updates["client_name"] = text
        updates["lead_step"] = "awaiting_phone"
        updates["response"] = msg["ask_phone"].format(name=text)
        return updates

    # Step 3: Await phone number
    if step == "awaiting_phone":
        detected_srv = FormValidator.detect_service(text)
        if detected_srv:
            updates["current_service"] = detected_srv

        phone = FormValidator.extract_phone(text)
        if not phone:
            updates["response"] = PHONE_REPROMPT.get(lang, PHONE_REPROMPT["en"])
            return updates

        updates["client_phone"] = phone
        updates["lead_step"] = "awaiting_email"
        updates["response"] = msg["ask_email"]
        return updates

    # Step 4: Await email and complete lead
    if step == "awaiting_email":
        detected_srv = FormValidator.detect_service(text)
        if detected_srv:
            updates["current_service"] = detected_srv

        email = FormValidator.extract_email(text)
        is_skip = text.lower() in ["ні", "нет", "no", "ne", "-", "пропустити", "пропустить", "немає", "нет емейла"]

        if not email and not is_skip:
            updates["response"] = EMAIL_REPROMPT.get(lang, EMAIL_REPROMPT["en"])
            return updates

        final_email = email if email else "Not specified"
        updates["client_email"] = final_email
        updates["lead_step"] = "completed"
        updates["response"] = msg["completed"]

        client_name = FormValidator.get_val(state, "client_name", "Not specified")
        client_phone = FormValidator.get_val(state, "client_phone", "Not specified")
        service = FormValidator.get_val(updates, "current_service") or FormValidator.get_val(state, "current_service") or FormValidator.extract_service_from_history(history)
        user = FormValidator.get_val(incoming, "user")

        await notify_manager_lead_telegram(
            client_name=client_name,
            client_phone=client_phone,
            client_email=final_email,
            service=service,
            user=user,
            lang=lang
        )
        
        log_event(
            "lead_captured",
            status="ok",
            name=client_name,
            phone=client_phone,
            email=final_email,
            service=service
        )
        return updates
    
    log_event("lead_capture_finished", status="ok", next_step=updates.get("lead_step"))

    return updates
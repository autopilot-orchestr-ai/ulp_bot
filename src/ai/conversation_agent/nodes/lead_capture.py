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

    updates = {}

    # 1. BREAK THE LOOP: If the form was already completed, wipe the state.
    if step == "completed":
        step = None
        updates.update({
            "lead_step": None,
            "current_service": None,
            "client_name": None,
            "client_phone": None,
            "client_email": None,
        })

    # 2. Profanity Check
    if await FormValidator.is_profanity_or_hostile(text):
        profanity_warnings = {
            "uk": "Будь ласка, дотримуйтесь коректного спілкування у чаті. Введіть дані коректно або задайте ваше питання.",
            "cs": "Prosím, udržujte v chatu slušnou komunikaci. Zadejte správné údaje nebo položte dotaz.",
            "en": "Please keep our communication respectful. Enter valid details or ask your question.",
            "ru": "Пожалуйста, соблюдайте корректное общение в чате. Введите данные корректно или задайте ваш вопрос."
        }
        updates.update({
            "route_to_llm": False,
            "response": profanity_warnings.get(lang, profanity_warnings["en"])
        })
        return updates

    # 3. Question Trapping: Pause booking ONLY if already in the middle of the form
    if step in ["awaiting_name", "awaiting_phone", "awaiting_email"] and await FormValidator.is_user_asking_question(text):
        updates.update({
            "route_to_llm": True   
        })
        return updates

    # 4. Cancel Check
    if await FormValidator.is_user_cancelling(text):
        cancel_msgs = {
            "uk": "Зрозумів, скасував запис. Якщо виникнуть питання — запитуйте!",
            "cs": "Rozumím, zrušil jsem záznam. Pokud budete mít dotazy, ptejte se!",
            "en": "Got it, I've canceled the booking. Let me know if you have any questions!",
            "ru": "Понял, отменил запись. Если возникнут вопросы — задавайте!"
        }
        updates.update({
            "lead_step": None,
            "current_service": None,
            "client_name": None,
            "client_phone": None,
            "client_email": None,
            "route_to_llm": False,
            "response": cancel_msgs.get(lang, cancel_msgs["uk"])
        })
        return updates

    # Step 1: Initialize form
    if not step or step == "start":
        service = FormValidator.extract_service_from_history(history, current_text=text)
        
        # If no specific service is mentioned yet, ask them to clarify instead of looping to LLM
        if not service:
            # We assume SERVICES_LIST_RESPONSE is a dict structured like {"en": "...", "cs": "..."}
            list_response = SERVICES_LIST_RESPONSE.get(lang, SERVICES_LIST_RESPONSE.get("en", "Please specify a service."))
            updates.update({
                "lead_step": None,
                "route_to_llm": False,
                "response": list_response
            })
            return updates

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

        if not await FormValidator.is_valid_name(text):
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

        phone = await FormValidator.extract_phone(text)
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

        email = await FormValidator.extract_email(text)
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
import re
from src.bots.utils.notify_stuff import notify_manager_lead_telegram
from src.ai.conversation_agent.state import AgentState
from src.logger import log_event

# Updated Imports: 
from src.ai.conversation_agent.agent_rules.strings import (
    MESSAGES, 
    WEEKEND_NOTICES, 
    PHONE_REPROMPT, 
    NAME_REPROMPT,
    SERVICES_LIST_RESPONSE,
    WHEN_WILL_YOU_CALL_RESPONSE, # Added this
    SERVICE_LOCALIZED_NAMES,
)

from src.ai.conversation_agent.agent_rules.lang import get_lang
from src.ai.conversation_agent.agent_rules.form_validator import FormValidator

async def lead_capture_node(state: AgentState) -> dict:
    log_event("lead_capture_start", status="start", step=FormValidator.get_val(state, "lead_step"))

    incoming = FormValidator.get_val(state, "incoming")
    raw_text = FormValidator.get_val(incoming, "text", "") or ""
    text = raw_text.strip()
    text_lower = text.lower()
    
    step = FormValidator.get_val(state, "lead_step")
    lang = get_lang(state)

    # 1. FIX LANGUAGE LOCK: Dynamic override if user switches language mid-funnel
    if re.search(r'[ěščřžýáíéóúůďťň]', text_lower) or any(w in text_lower for w in ["potřebuju", "chci", "česky", "nerozumím"]):
        lang = "cs"
    elif re.search(r'[ыъэё]', text_lower) or any(w in text_lower for w in ["пожалуйста", "нужен", "хочу"]):
        lang = "ru"
    elif re.search(r'[іїєґ]', text_lower) or any(w in text_lower for w in ["потріб", "хочу", "будь ласка"]):
        lang = "uk"

    msg = MESSAGES.get(lang, MESSAGES["en"])
    history = FormValidator.get_val(state, "conversation_history", [])

    updates = {}

    # 2. BREAK THE LOOP: If the form was already completed, wipe the state.
    if step == "completed":
        step = None
        updates.update({
            "lead_step": None,
            "current_service": None,
            "client_name": None,
            "client_phone": None,
            "client_email": None,
        })

    # 3. Profanity Check
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

    # 4. "WHEN WILL YOU CALL ME?" INTERCEPTOR
    has_time = any(k in text_lower for k in ["коли", "when", "kdy", "во сколько"])
    has_call = any(k in text_lower for k in ["зателефону", "call", "zavol", "позвон", "зв'яж", "kontakt"])
    if has_time and has_call:
        updates.update({
            "route_to_llm": False,
            # FIX: Use the new variable name here instead of WORKING_HOURS_MSG
            "response": WHEN_WILL_YOU_CALL_RESPONSE.get(lang, WHEN_WILL_YOU_CALL_RESPONSE["en"]) 
        })
        return updates

    # 5. FIX QUESTION/CONFUSION TRAP
    is_q = await FormValidator.is_user_asking_question(text)
    # Hardcoded safety net: if LLM fails, but obvious signs of confusion/questions exist
    if not is_q and ("?" in text or "nerozumím" in text_lower or "не розумію" in text_lower or "не понимаю" in text_lower):
        is_q = True

    if step in ["awaiting_name", "awaiting_phone", "awaiting_email"] and is_q:
        updates.update({
            "route_to_llm": True   
        })
        return updates

    # 6. Cancel Check
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
        
        # STRICT FIX: Catch None type, empty strings, and the literal string "None"
        if not service or str(service).strip().lower() == "none" or str(service).strip() == "":
            list_response = SERVICES_LIST_RESPONSE.get(lang, SERVICES_LIST_RESPONSE["en"])
            updates.update({
                "lead_step": "awaiting_service",
                "route_to_llm": False,
                "response": list_response
            })
            return updates

        # If a valid service IS found:
        updates["lead_step"] = "awaiting_name"
        updates["current_service"] = service

        start_response = msg.get("start", "")
        if FormValidator.has_weekend_mention(text):
            notice = WEEKEND_NOTICES.get(lang, WEEKEND_NOTICES["en"])
            start_response = notice + start_response

        updates["response"] = start_response
        return updates

    # Step 1.5: Await Service Selection
    if step == "awaiting_service":
        detected_id = FormValidator.detect_service(text)
        
        if detected_id:
            # We save the clean ID to the database/CRM state
            updates["current_service"] = detected_id
            updates["lead_step"] = "awaiting_name"
            
            # Fetch the beautifully translated name for the chat interface!
            # (Requires importing SERVICE_LOCALIZED_NAMES from your validator file)
            localized_srv = SERVICE_LOCALIZED_NAMES.get(detected_id, {}).get(lang, detected_id)
            
            reprompt = {
                "en": f"Got it, you are interested in the service: **{localized_srv}**!\n\nHow should I address you? Please enter your **Full Name**:",
                "cs": f"Rozumím, máte zájem o službu: **{localized_srv}**!\n\nJak vás mohu oslovovat? Uveďte prosím vaše **Jméno a Příjmení**:",
                "uk": f"Зрозумів, вас цікавить послуга: **{localized_srv}**!\n\nА як до вас звертатися? Вкажіть, будь ласка, ваше **Прізвище та Ім'я**:",
                "ru": f"Понял, вас интересует услуга: **{localized_srv}**!\n\nКак к вам обращаться? Укажите, пожалуйста, ваше **Имя и Фамилию**:",
            }
            updates["response"] = reprompt.get(lang, reprompt["en"])
            return updates
        else:
            # LOOP BREAKER (as implemented previously)
            updates.update({
                "route_to_llm": True,
                "lead_step": None 
            })
            return updates
        
    # Step 2: Await full name
    if step == "awaiting_name":
        detected_srv = FormValidator.detect_service(text)
        if detected_srv:
            updates["current_service"] = detected_srv
            
            # FIX: Fetch the beautifully translated name!
            localized_srv = SERVICE_LOCALIZED_NAMES.get(detected_srv, {}).get(lang, detected_srv)
            
            reprompt = {
                "en": f"Got it, you are interested in **{localized_srv}**!\n\nHow should I address you? Please enter your **Full Name**:",
                "cs": f"Rozumím, máte zájem o **{localized_srv}**!\n\nJak vás mohu oslovovat? Uveďte prosím vaše **Jméno a Příjmení**:",
                "uk": f"Зрозумів, вас цікавить **{localized_srv}**!\n\nА як до вас звертатися? Вкажіть, будь ласка, ваше **Прізвище та Ім'я**:",
                "ru": f"Понял, вас интересует **{localized_srv}**!\n\nКак к вам обращаться? Укажите, пожалуйста, ваше **Имя и Фамилию**:",
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

        # This will crash if EMAIL_REPROMPT no longer exists in strings.py!
        if not email and not is_skip:
            updates["response"] = msg["ask_email"]
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
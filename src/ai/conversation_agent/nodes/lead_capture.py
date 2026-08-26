import re
from dataclasses import dataclass
from typing import Any, Optional

from src.bots.utils.notify_stuff import notify_manager_lead_telegram
from src.ai.conversation_agent.state import AgentState
from src.logger import log_event
from src.ai.conversation_agent.routes import Route

from src.ai.conversation_agent.agent_rules.strings import (
    MESSAGES,
    WEEKEND_NOTICES,
    PHONE_REPROMPT,
    NAME_REPROMPT,
    SERVICES_LIST_RESPONSE,
    WHEN_WILL_YOU_CALL_RESPONSE,
    SERVICE_LOCALIZED_NAMES,
)
from src.ai.conversation_agent.agent_rules.form_validator import FormValidator

# Import centralized language detection
from src.bots.utils.language_detection import detect_lang

_RESET_FIELDS = {
    "lead_step": None,
    "current_service": None,
    "client_name": None,
    "client_phone": None,
    "client_email": None,
}

_CANCEL_MESSAGES = {
    "uk": "Зрозумів, скасував запис. Якщо виникнуть питання — запитуйте!",
    "cs": "Rozumím, zrušil jsem záznam. Pokud budete mít dotazy, ptejte se!",
    "en": "Got it, I've canceled the booking. Let me know if you have any questions!",
    "ru": "Понял, отменил запись. Если возникнут вопросы — задавайте!",
}

_SKIP_EMAIL_WORDS = {"ні", "нет", "no", "ne", "-", "пропустити", "пропустить", "немає", "нет емейла"}


def _service_reprompt(service_id: str, lang: str) -> str:
    localized = SERVICE_LOCALIZED_NAMES.get(service_id, {}).get(lang, service_id)
    templates = {
        "en": f"Got it, you are interested in **{localized}**!\n\nHow should I address you? Please enter your **Full Name**:",
        "cs": f"Rozumím, máte zájem o **{localized}**!\n\nJak vás mohu oslovovat? Uveďte prosím vaše **Jméno a Příjmení**:",
        "uk": f"Зрозумів, вас цікавить **{localized}**!\n\nА як до вас звертатися? Вкажіть, будь ласка, ваше **Прізвище та Ім'я**:",
        "ru": f"Понял, вас интересует **{localized}**!\n\nКак к вам обращаться? Укажите, пожалуйста, ваше **Имя и Фамилию**:",
    }
    return templates.get(lang, templates["en"])


# Step intercepts checked before handler execution
async def _check_call_timing(state: AgentState, step: Optional[str]) -> Optional[dict]:
    if not FormValidator.is_asking_call_timing(state.incoming.text):
        return None
    return {
        "route_to_llm": False,
        "response": WHEN_WILL_YOU_CALL_RESPONSE.get(state.language, WHEN_WILL_YOU_CALL_RESPONSE["en"]),
    }

async def _check_question_trap(state: AgentState, step: Optional[str]) -> Optional[dict]:
    if step not in ("awaiting_name", "awaiting_phone", "awaiting_email"):
        return None
    text_lower = state.incoming.text.lower()
    is_q = await FormValidator.is_user_asking_question(state.incoming.text)
    if not is_q and ("?" in state.incoming.text or "nerozumím" in text_lower or "не розумію" in text_lower or "не понимаю" in text_lower):
        is_q = True
    return {"route": Route.CHAT} if is_q else None

async def _check_cancel(state: AgentState, step: Optional[str]) -> Optional[dict]:
    if not await FormValidator.is_user_cancelling(state.incoming.text):
        return None
    return {
        **_RESET_FIELDS,
        "route_to_llm": False,
        "response": _CANCEL_MESSAGES.get(state.language, _CANCEL_MESSAGES["uk"]),
    }

_INTERCEPTS = (_check_call_timing, _check_question_trap, _check_cancel)


async def _step_start(state: AgentState) -> dict:
    service = (
        state.current_service
        or FormValidator.extract_service_from_history(
            state.conversation_history,
            current_text=state.incoming.text,
        )
        or FormValidator.detect_service(state.incoming.text)
    )

    if not service:
        return {
            "lead_step": "awaiting_service",
            "route_to_llm": False,
            "response": SERVICES_LIST_RESPONSE.get(
                state.language,
                SERVICES_LIST_RESPONSE["en"],
            ),
        }

    return {
        "current_service": service,
        "lead_step": "awaiting_name",
        "route_to_llm": False,
        "response": _service_reprompt(
            service,
            state.language,
        ),
    }

async def _step_awaiting_service(state: AgentState) -> dict:
    detected_id = FormValidator.detect_service(state.incoming.text)
    if not detected_id:
        return {"route_to_llm": True, "lead_step": None}

    if not FormValidator.has_price_been_shown(state.conversation_history):
        return {"route_to_llm": True, "current_service": detected_id}

    return {
        "current_service": detected_id,
        "lead_step": "awaiting_name",
        "response": _service_reprompt(detected_id, state.language),
    }

async def _step_awaiting_name(state: AgentState) -> dict:
    service = FormValidator.detect_service(state.incoming.text)

    if service:
        return {
            "current_service": service,
            "response": _service_reprompt(
                service,
                state.language,
            ),
        }

    if await FormValidator.is_user_asking_question(
        state.incoming.text
    ):
        return {
            "route_to_llm": True,
        }

    name = state.incoming.text.strip()

    if not await FormValidator.is_valid_name(name):
        return {
            "route_to_llm": False,
            "response": NAME_REPROMPT.get(
                state.language,
                NAME_REPROMPT["en"],
            ),
        }

    msg = MESSAGES.get(state.language, MESSAGES["uk"])
    return {
        "client_name": name,
        "lead_step": "awaiting_phone",
        "route": Route.LEAD,
        "response": msg["ask_phone"].format(name=name),
    }

async def _step_awaiting_phone(state: AgentState) -> dict:
    phone = await FormValidator.extract_phone(
        state.incoming.text
    )

    if not phone:
        return {
            "route_to_llm": False,
            "response": PHONE_REPROMPT.get(
                state.language,
                PHONE_REPROMPT["en"],
            ),
        }

    msg = MESSAGES.get(state.language, MESSAGES["uk"])
    return {
        "client_phone": phone,
        "lead_step": "awaiting_email",
        "route": Route.LEAD,
        "response": msg["ask_email"],
    }

async def _step_awaiting_email(state: AgentState) -> dict:
    text = state.incoming.text.strip()
    email = await FormValidator.extract_email(text)

    is_skip = text.lower() in _SKIP_EMAIL_WORDS

    if not email and not is_skip:
        return {
            "route_to_llm": False,
            "response": state.msg["ask_email"],
        }

    final_email = email or None

    client_name = state.client_name or "Not specified"
    client_phone = state.client_phone or "Not specified"
    service = (
        state.current_service
        or FormValidator.extract_service_from_history(
            state.conversation_history
        )
        or "Not specified"
    )

    await notify_manager_lead_telegram(
        client_name=client_name,
        client_phone=client_phone,
        client_email=final_email or "Not specified",
        service=service,
        user=state.incoming.user,
        lang=state.language,
    )

    msg = MESSAGES.get(state.language, MESSAGES["uk"])
    return {
        "client_email": final_email,
        "lead_step": "completed",
        "route": Route.END,
        "response": msg["completed"],
    }

_STEP_HANDLERS = {
    None: _step_start,
    "start": _step_start,
    "awaiting_service": _step_awaiting_service,
    "awaiting_name": _step_awaiting_name,
    "awaiting_phone": _step_awaiting_phone,
    "awaiting_email": _step_awaiting_email,
}

async def lead_capture_node(state: AgentState) -> dict:
    text = (state.incoming.text or "").strip()
    step = state.lead_step

    log_event("lead_capture_start", status="start", step=step, text=text)

    active_lang = state.language or "uk"
    lang = detect_lang(text, default=active_lang)
    state.language = lang
    
    # Дістаємо словник повідомлень для мови
    msg = MESSAGES.get(lang, MESSAGES["uk"])

    if step == "completed":
        step = None

    for check in _INTERCEPTS:
        result = await check(state, step)
        if result is not None:
            # Якщо потрібно передати питання в LLM (info agent)
            if result.get("route_to_llm"):
                result["route"] = Route.CHAT
            log_event("lead_capture_intercept", status="ok", step=step)
            return result

    handler = _STEP_HANDLERS.get(step, _step_start)
    result = await handler(state)

    # Якщо хендлер каже передати управління в LLM
    if result.get("route_to_llm"):
        result["route"] = Route.CHAT
    elif result.get("lead_step") == "completed":
        result["route"] = Route.END
    else:
        result["route"] = Route.LEAD

    log_event("lead_capture_finished", status="ok", next_step=result.get("lead_step", step))
    return result
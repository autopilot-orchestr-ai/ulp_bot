import re
from dataclasses import dataclass
from typing import Any, Optional

from src.bots.utils.notify_stuff import notify_manager_lead_telegram
from src.ai.conversation_agent.state import AgentState
from src.logger import log_event

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

# Import the single source of truth for language
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


@dataclass
class LeadCtx:
    state: AgentState
    incoming: Any
    text: str
    lang: str
    msg: dict
    history: list

def _service_reprompt(service_id: str, lang: str) -> str:
    localized = SERVICE_LOCALIZED_NAMES.get(service_id, {}).get(lang, service_id)
    templates = {
        "en": f"Got it, you are interested in **{localized}**!\n\nHow should I address you? Please enter your **Full Name**:",
        "cs": f"Rozumím, máte zájem o **{localized}**!\n\nJak vás mohu oslovovat? Uveďte prosím vaše **Jméno a Příjmení**:",
        "uk": f"Зрозумів, вас цікавить **{localized}**!\n\nА як до вас звертатися? Вкажіть, будь ласка, ваше **Прізвище та Ім'я**:",
        "ru": f"Понял, вас интересует **{localized}**!\n\nКак к вам обращаться? Укажите, пожалуйста, ваше **Имя и Фамилию**:",
    }
    return templates.get(lang, templates["en"])

async def _check_call_timing(ctx: LeadCtx, step: Optional[str]) -> Optional[dict]:
    if not FormValidator.is_asking_call_timing(ctx.text):
        return None
    return {
        "route_to_llm": False,
        "response": WHEN_WILL_YOU_CALL_RESPONSE.get(ctx.lang, WHEN_WILL_YOU_CALL_RESPONSE["en"]),
    }

async def _check_question_trap(ctx: LeadCtx, step: Optional[str]) -> Optional[dict]:
    if step not in ("awaiting_name", "awaiting_phone", "awaiting_email"):
        return None
    text_lower = ctx.text.lower()
    is_q = await FormValidator.is_user_asking_question(ctx.text)
    if not is_q and ("?" in ctx.text or "nerozumím" in text_lower or "не розумію" in text_lower or "не понимаю" in text_lower):
        is_q = True 
    return {"route_to_llm": True} if is_q else None

async def _check_cancel(ctx: LeadCtx, step: Optional[str]) -> Optional[dict]:
    if not await FormValidator.is_user_cancelling(ctx.text):
        return None
    return {
        **_RESET_FIELDS,
        "route_to_llm": False,
        "response": _CANCEL_MESSAGES.get(ctx.lang, _CANCEL_MESSAGES["uk"]),
    }

_INTERCEPTS = (_check_call_timing, _check_question_trap, _check_cancel)

async def _step_start(ctx: LeadCtx) -> dict:
    service = FormValidator.extract_service_from_history(ctx.history, current_text=ctx.text)

    if not service or str(service).strip().lower() in ("", "none"):
        return {
            "lead_step": "awaiting_service",
            "route_to_llm": False,
            "response": SERVICES_LIST_RESPONSE.get(ctx.lang, SERVICES_LIST_RESPONSE["en"]),
        }

    start_response = ctx.msg.get("start", "")
    if FormValidator.has_weekend_mention(ctx.text):
        start_response = WEEKEND_NOTICES.get(ctx.lang, WEEKEND_NOTICES["en"]) + start_response

    return {
        "lead_step": "awaiting_name",
        "current_service": service,
        "response": start_response,
    }

async def _step_awaiting_service(ctx: LeadCtx) -> dict:
    detected_id = FormValidator.detect_service(ctx.text)
    if not detected_id:
        return {"route_to_llm": True, "lead_step": None}
    
    return {
        "current_service": detected_id,
        "lead_step": "awaiting_name",
        "response": _service_reprompt(detected_id, ctx.lang),
    }

async def _step_awaiting_name(ctx: LeadCtx) -> dict:
    detected_srv = FormValidator.detect_service(ctx.text)
    if detected_srv:
        return {"current_service": detected_srv, "response": _service_reprompt(detected_srv, ctx.lang)}

    if not await FormValidator.is_valid_name(ctx.text):
        return {"response": NAME_REPROMPT.get(ctx.lang, NAME_REPROMPT["en"])}

    return {
        "client_name": ctx.text,
        "lead_step": "awaiting_phone",
        "response": ctx.msg["ask_phone"].format(name=ctx.text),
    }

async def _step_awaiting_phone(ctx: LeadCtx) -> dict:
    updates: dict = {}
    detected_srv = FormValidator.detect_service(ctx.text)
    if detected_srv:
        updates["current_service"] = detected_srv

    phone = await FormValidator.extract_phone(ctx.text)
    if not phone:
        updates["response"] = PHONE_REPROMPT.get(ctx.lang, PHONE_REPROMPT["en"])
        return updates

    updates["client_phone"] = phone
    updates["lead_step"] = "awaiting_email"
    updates["response"] = ctx.msg["ask_email"]
    return updates

async def _step_awaiting_email(ctx: LeadCtx) -> dict:
    updates: dict = {}
    detected_srv = FormValidator.detect_service(ctx.text)
    if detected_srv:
        updates["current_service"] = detected_srv

    email = await FormValidator.extract_email(ctx.text)
    is_skip = ctx.text.lower() in _SKIP_EMAIL_WORDS

    if not email and not is_skip:
        updates["response"] = ctx.msg["ask_email"]
        return updates

    final_email = email or "Not specified"
    updates["client_email"] = final_email
    updates["lead_step"] = "completed"
    updates["response"] = ctx.msg["completed"]

    client_name = FormValidator.get_val(ctx.state, "client_name", "Not specified")
    client_phone = FormValidator.get_val(ctx.state, "client_phone", "Not specified")
    service = (
        updates.get("current_service")
        or FormValidator.get_val(ctx.state, "current_service")
        or FormValidator.extract_service_from_history(ctx.history)
    )
    user = FormValidator.get_val(ctx.incoming, "user")

    await notify_manager_lead_telegram(
        client_name=client_name,
        client_phone=client_phone,
        client_email=final_email,
        service=service,
        user=user,
        lang=ctx.lang,
    )
    log_event("lead_captured", status="ok", name=client_name, phone=client_phone, email=final_email, service=service)
    return updates

_STEP_HANDLERS = {
    None: _step_start,
    "start": _step_start,
    "awaiting_service": _step_awaiting_service,
    "awaiting_name": _step_awaiting_name,
    "awaiting_phone": _step_awaiting_phone,
    "awaiting_email": _step_awaiting_email,
}

async def lead_capture_node(state: AgentState) -> dict:
    incoming = FormValidator.get_val(state, "incoming")
    text = (FormValidator.get_val(incoming, "text", "") or "").strip()
    step = FormValidator.get_val(state, "lead_step")

    log_event("lead_capture_start", status="start", step=step)

    # Clean, unified language detection
    current_state_lang = getattr(state, "language", None) or "uk"
    lang = detect_lang(text, default=current_state_lang)
    
    ctx = LeadCtx(
        state=state,
        incoming=incoming,
        text=text,
        lang=lang,
        msg=MESSAGES.get(lang, MESSAGES["en"]),
        history=FormValidator.get_val(state, "conversation_history", []),
    )

    reset = {}
    if step == "completed":
        step = None
        reset = dict(_RESET_FIELDS)

    for check in _INTERCEPTS:
        result = await check(ctx, step)
        if result is not None:
            return {**reset, **result}

    handler = _STEP_HANDLERS.get(step, _step_start)
    result = await handler(ctx)

    log_event("lead_capture_finished", status="ok", next_step=result.get("lead_step", step))
    return {**reset, **result}
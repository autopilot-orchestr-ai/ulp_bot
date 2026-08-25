from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai.conversation_agent.state import AgentState
from src.config import settings
from src.ai.knowledge.llm import get_llm
from src.logger import log_event
# from src.ai.conversation_agent.agent_rules.lang import detect_lang
from src.ai.conversation_agent.agent_rules.form_validator import FormValidator
from src.ai.conversation_agent.prompts.supervisor import SYSTEM_PROMPT
from src.bots.utils.language_detection import should_redetect_language, detect_lang
from src.bots.utils.notify_stuff import notify_manager_aggressive_telegram


class IntentClassification(BaseModel):
    intent: Literal["info_intent", "lead_intent", "greeting", "unknown", "off_topic", "call_timing"]
    service_name: str | None = Field(
        default=None,
        description="Name of the service mentioned by the user if applicable (e.g. 'Консультація', 'Судові переклади', 'Довіреність', 'Апостиль'). If not mentioned, set to None."
    )
    is_aggressive: bool = Field(
        default=False,
        description="True if the message contains hostility, insults, threats, or profanity directed at the bot or staff."
    )


async def classify_intent(state: AgentState) -> dict:
    default_lang = getattr(state, "language", None) or "uk"
    
    is_in_lead_form = getattr(state, "lead_step", None) is not None or getattr(state, "active_form", None) is not None

    if is_in_lead_form:
        lang = default_lang
    elif should_redetect_language(state.incoming.text, current_lang=default_lang):
        detected = detect_lang(state.incoming.text)
        lang = detected if detected else default_lang
    else:
        lang = default_lang

    if FormValidator.is_asking_call_timing(state.incoming.text):
        return {
            "intent": "call_timing",
            "language": lang,
            "current_service": getattr(state, "current_service", None),
            "retrieved_context": None,
        }

    # ==========================================
    # NEW FIX: CATCH "ANO/YES" AND FORCE LEAD INTENT
    # ==========================================
    text_lower = state.incoming.text.lower().strip()
    affirmative_words = {"ano", "yes", "так", "да", "chci"}
    
    last_bot_msg = ""
    for m in reversed(state.conversation_history):
        if m["role"] == "assistant":
            last_bot_msg = m["content"].lower()
            break
            
    # If the bot just asked a Yes/No question about contacting a manager:
    if "(ano / ne)" in last_bot_msg or "kontaktoval" in last_bot_msg:
        # If the user's response starts with an affirmative word:
        if any(text_lower.startswith(w) for w in affirmative_words) or text_lower == "a":
            log_event("intent_classified", status="forced_lead_intent", reason="user_confirmed_manager")
            return {
                "intent": "lead_intent",
                "language": lang,
                "current_service": getattr(state, "current_service", None),
                "retrieved_context": None,
            }
    # ==========================================

    llm = get_llm(settings.llm_model)
    structured_llm = llm.with_structured_output(IntentClassification)

    history_messages = []
    for m in state.conversation_history[-4:]:
        if m["role"] == "user":
            history_messages.append(HumanMessage(content=m["content"]))
        else:
            history_messages.append(AIMessage(content=m["content"]))

    log_event("intent_classifying", status="start", text=state.incoming.text)
    try:
        result: IntentClassification = await structured_llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            *history_messages,
            HumanMessage(content=state.incoming.text),
        ])
        log_event("intent_classified", status="ok", intent=result.intent)

        if result.is_aggressive:
            log_event("aggressive_message_flagged", status="ok", text=state.incoming.text)
            try:
                await notify_manager_aggressive_telegram(
                    client_id=state.incoming.client_id,
                    client_name=state.incoming.client_name,
                    text=state.incoming.text,
                    lang=lang,
                )
            except Exception:
                pass  # never let a notification failure break the reply to the user

        existing_service = getattr(state, "current_service", None)
        detected_service = result.service_name or existing_service

        return {
            "intent": result.intent,
            "language": lang,
            "current_service": detected_service,
            "retrieved_context": None,
        }
    except Exception as exc:
        log_event("intent_classified", status="error", error=str(exc))
        raise
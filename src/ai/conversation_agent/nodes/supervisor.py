from typing import Literal
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai.conversation_agent.state import AgentState
from src.config import settings
from src.ai.knowledge.llm import get_llm
from src.logger import log_event
from src.ai.conversation_agent.agent_rules.form_validator import FormValidator
from src.ai.conversation_agent.prompts.supervisor import SYSTEM_PROMPT
from src.ai.conversation_agent.routes import Route

# Import centralized language detection
from src.bots.utils.language_detection import detect_lang
from src.bots.utils.notify_stuff import notify_manager_aggressive_telegram

class IntentClassification(BaseModel):
    intent: Literal["info_intent", "lead_intent", "greeting", "unknown", "off_topic", "call_timing"]
    service_name: str | None = Field(
        default=None,
        description="Name of the service mentioned by the user if applicable. If not mentioned, set to None."
    )
    is_aggressive: bool = Field(
        default=False,
        description="True if the message contains hostility, insults, threats, or profanity."
    )

def map_intent_to_route(intent: str) -> Route:
    match intent:
        case "info_intent" | "greeting" | "unknown":
            return Route.INFO

        case "lead_intent":
            return Route.LEAD

        case "off_topic":
            return Route.OFF_TOPIC

        case "call_timing":
            return Route.CALL_TIMING

        case _:
            return Route.HUMAN

async def classify_intent(state: AgentState) -> dict:
    default_lang = getattr(state, "language", None) or "uk"
    is_in_lead_form = state.lead_step is not None

    # Resolve active language
    if is_in_lead_form:
        lang = default_lang
    else:
        lang = detect_lang(state.incoming.text, default=default_lang)

    # Call timing intercept ("When will you call me?")
    if FormValidator.is_asking_call_timing(state.incoming.text):
        return {
            "intent": "call_timing",
            "route": Route.CALL_TIMING,
            "language": lang,
            "current_service": getattr(state, "current_service", None),
            "retrieved_context": None,
        }

    # YES/ANO/ТАК INTERCEPT 
    text_lower = state.incoming.text.lower().strip()
    affirmative_words = {"ano", "yes", "так", "да", "chci", "y"}
    last_bot_msg = ""
    for m in reversed(state.conversation_history):
        if m["role"] == "assistant":
            last_bot_msg = m["content"].lower()
            break
            
    manager_prompts = [
        "(ano / ne)", "(yes / no)", "(так / ні)", "(да / нет)", 
        "kontaktoval", "contact", "зв'яжеться", "свяжется", "contact you"
    ]
    
    if any(prompt in last_bot_msg for prompt in manager_prompts):
        if any(text_lower.startswith(w) for w in affirmative_words) or text_lower == "a":
            log_event("intent_classified", status="forced_lead_intent", reason="user_confirmed_manager")
            return {
                "intent": "lead_intent",
                "route": Route.LEAD,
                "language": lang,
                "current_service": getattr(state, "current_service", None),
                "retrieved_context": None,
            }

    # Default LLM Routing
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
                pass 

        existing_service = getattr(state, "current_service", None)
        detected_service = result.service_name or existing_service

        return {
            "intent": result.intent,
            "route": map_intent_to_route(result.intent),
            "language": lang,
            "current_service": detected_service,
            "retrieved_context": None,
        }
    except Exception as exc:
        log_event("intent_classified", status="error", error=str(exc))
        raise
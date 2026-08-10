from typing import Literal
from pydantic import BaseModel
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai.conversation_agent.state import AgentState
from src.config import settings
from src.ai.knowledge.llm import get_llm
from src.logger import log_event
from src.ai.conversation_agent.data.lang import detect_lang
from src.ai.conversation_agent.prompts.superviser import SYSTEM_PROMPT
from src.bots.utils.language_detection import should_redetect_language, detect_lang


class IntentClassification(BaseModel):
    intent: Literal["info_intent", "lead_intent", "greeting", "unknown", "off_topic"]


async def classify_intent(state: AgentState) -> dict:
    llm = get_llm(settings.llm_model)
    structured_llm = llm.with_structured_output(IntentClassification)

    default_lang = getattr(state, "language", None) or "uk"
    
    is_in_lead_form = getattr(state, "lead_step", None) is not None or getattr(state, "active_form", None) is not None

    if is_in_lead_form:
        lang = default_lang
    elif should_redetect_language(state.incoming.text, current_lang=default_lang):
        detected = detect_lang(state.incoming.text)
        lang = detected if detected else default_lang
    else:
        lang = default_lang

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
        return {
            "intent": result.intent,
            "language": lang,
            "current_service": None,
            "retrieved_context": None,
        }
    except Exception as exc:
        log_event("intent_classified", status="error", error=str(exc))
        raise
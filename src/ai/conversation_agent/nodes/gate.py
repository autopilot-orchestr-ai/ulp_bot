from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai.conversation_agent.prompts.gate import SYSTEM_PROMPT
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState
from src.ai.llm import get_llm
from src.bots.utils.language_detection import detect_lang
from src.bots.utils.notify_stuff import notify_manager_aggressive_telegram
from src.config import settings
from src.logger import log_event

_AFFIRMATIVE_WORDS = {"ano", "yes", "так", "да", "chci", "y"}
_MANAGER_PROMPT_MARKERS = [
    "(ano / ne)", "(yes / no)", "(так / ні)", "(да / нет)",
    "kontaktoval", "contact", "зв'яжеться", "свяжется", "contact you",
]


class LeadGateClassification(BaseModel):
    wants_lead: bool = Field(
        description=(
            "True if the user shows a clear commitment to proceed - wants to "
            "order/book a specific service, explicitly wants a human/manager "
            "to contact them, or describes their personal legal situation "
            "asking for advice on it. False for everything else, including a "
            "bare mention of a service or a general question about it."
        )
    )
    is_aggressive: bool = Field(
        default=False,
        description="True if the message contains hostility, insults, threats, or profanity.",
    )


def _last_bot_message(history: list[dict]) -> str:
    for m in reversed(history):
        if m["role"] == "assistant":
            return m["content"].lower()
    return ""


def is_affirmative_reply_to_manager_prompt(text: str, history: list[dict]) -> bool:
    """True if the bot's last message asked "want us to contact you?" and
    this reply is a bare "yes"-shaped answer - short-circuits the LLM call
    for this very common, very unambiguous turn."""
    text_lower = text.lower().strip()
    last_bot_msg = _last_bot_message(history)
    if not any(marker in last_bot_msg for marker in _MANAGER_PROMPT_MARKERS):
        return False
    return text_lower == "a" or any(text_lower.startswith(w) for w in _AFFIRMATIVE_WORDS)


async def classify_lead_intent(state: AgentState) -> dict:
    default_lang = getattr(state, "language", None) or "uk"
    lang = detect_lang(state.incoming.text, default=default_lang)

    if is_affirmative_reply_to_manager_prompt(state.incoming.text, state.conversation_history):
        log_event("gate_classified", status="forced_lead", reason="user_confirmed_manager")
        return {"intent": "lead", "route": Route.LEAD, "language": lang}

    llm = get_llm(settings.llm_model)
    structured_llm = llm.with_structured_output(LeadGateClassification)

    history_messages = []
    for m in state.conversation_history[-4:]:
        cls = HumanMessage if m["role"] == "user" else AIMessage
        history_messages.append(cls(content=m["content"]))

    log_event("gate_classifying", status="start", text=state.incoming.text)
    try:
        result: LeadGateClassification = await structured_llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            *history_messages,
            HumanMessage(content=state.incoming.text),
        ])
    except Exception as exc:
        log_event("gate_classified", status="error", error=str(exc))
        raise

    log_event("gate_classified", status="ok", wants_lead=result.wants_lead)

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

    return {
        "intent": "lead" if result.wants_lead else "chat",
        "route": Route.LEAD if result.wants_lead else Route.CHAT,
        "language": lang,
    }

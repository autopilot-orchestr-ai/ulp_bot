import re

from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai.conversation_agent.agent_rules.affirmation import is_affirmative
from src.ai.conversation_agent.agent_rules.strings import PROFANITY_PATTERNS
from src.ai.conversation_agent.prompts.gate import SYSTEM_PROMPT
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState
from src.ai.llm import get_llm
from src.bots.utils.language_detection import detect_lang
from src.config import settings
from src.logger import log_event

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
    explicit_human_request: bool = Field(
        default=False,
        description=(
            "True specifically when the user explicitly asks to speak with a "
            "human, wants the manager/team to contact them, or is frustrated "
            "or insistent about being reached - as opposed to just wanting to "
            "book a specific service or describing their case for advice. "
            "This is a stronger, more urgent signal than wants_lead alone: it "
            "should only be true when wants_lead is also true."
        ),
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
    last_bot_msg = _last_bot_message(history)
    if not any(marker in last_bot_msg for marker in _MANAGER_PROMPT_MARKERS):
        return False
    return is_affirmative(text)


async def classify_lead_intent(state: AgentState) -> dict:
    default_lang = getattr(state, "language", None) or "uk"

    if state.lead_step is not None and state.lead_step != "completed":
        # route_after_gate overrides whatever we return here when a form is
        # active, so skip the LLM classification call entirely (it would be
        # discarded). Still run a cheap regex-only profanity check purely for
        # log visibility - staff are only ever pinged on Telegram for the two
        # cases the user set as policy (explicit human request, or a
        # completed lead with contact details), not for hostility alone.
        log_event("gate_classified", status="skipped_mid_form", lead_step=state.lead_step, language=default_lang)
        if any(re.search(pattern, state.incoming.text) for pattern in PROFANITY_PATTERNS):
            log_event("aggressive_message_flagged", status="ok", text=state.incoming.text, source="regex_mid_form")
        return {"intent": "lead", "route": Route.LEAD, "language": default_lang}

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

    log_event(
        "gate_classified",
        status="ok",
        wants_lead=result.wants_lead,
        explicit_human_request=result.explicit_human_request,
        is_aggressive=result.is_aggressive,
        language=lang,
    )

    # Logged for visibility, but not sent to staff on Telegram: per user
    # policy (2026-08-26), the manager is only ever notified for a
    # completed lead with contact details, not for hostility alone.
    if result.is_aggressive:
        log_event("aggressive_message_flagged", status="ok", text=state.incoming.text)

    # explicit_human_request is still classified and logged above for
    # visibility, but per user policy (2026-08-27) it no longer pages staff
    # on its own, for now - it was firing on messages like "call me on
    # Saturday" (a call-timing question, not a genuine escalation) and
    # promising a callback the bot has no contact details to make good on.
    # notify_manager_human_request_telegram (notify_stuff.py) still exists
    # but nothing calls it anymore - same pattern as
    # notify_manager_aggressive_telegram above.

    return {
        "intent": "lead" if result.wants_lead else "chat",
        "route": Route.LEAD if result.wants_lead else Route.CHAT,
        "language": lang,
    }

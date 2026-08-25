import uuid
from src.ai.conversation_agent.state import AgentState
from src.config import settings
from src.logger import log_event
from src.ai.conversation_agent.prompts.escalation import HANDOFF_MESSAGES
from src.bots.utils.notify_stuff import notify_manager_lead_telegram
from src.api_client.core_api import core_api
from src.bots.utils.language_detection import detect_lang 


async def get_or_create_conversation_id() -> uuid.UUID:
    """Returns the UUID for this conversation (stub — full version in router.py)."""
    return uuid.uuid4()


async def escalate(state: AgentState) -> dict:
    conversation_id = await get_or_create_conversation_id()

    # FIX: Pass state.incoming.text instead of state
    await core_api.store_unanswered_question(conversation_id, state.incoming.text)

    staff_notified = bool(settings.staff_telegram_chat_id)
    try:
        await notify_manager_lead_telegram(state.incoming.text)
    except Exception:
        staff_notified = False
    log_event("escalation_triggered", status="ok", question=state.incoming.text, staff_notified=staff_notified)

    client_lang = detect_lang(state.incoming.text) if state.incoming.text else "uk"

    return {"response": HANDOFF_MESSAGES.get(client_lang, HANDOFF_MESSAGES["uk"])}
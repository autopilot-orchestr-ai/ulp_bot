from src.ai.conversation_agent.graph import graph
from src.schemas.ai.messages import IncomingMessage
from src.api_client.core_api import core_api
from src.logger import log_event

# Last-resort text if a graph run somehow produces no response — should never
# be seen in normal operation, it just guarantees we never send Telegram an empty message.
_EMPTY_RESPONSE_FALLBACK = {
    "uk": "Перепрошую, сталася технічна помилка. Спробуйте, будь ласка, ще раз або зателефонуйте нам за +420 703 614 444.",
    "cs": "Omlouváme se, došlo k technické chybě. Zkuste to prosím znovu nebo nám zavolejte na +420 703 614 444.",
    "ru": "Извините, произошла техническая ошибка. Попробуйте, пожалуйста, ещё раз или позвоните нам по +420 703 614 444.",
    "en": "Sorry, something went wrong on our end. Please try again or call us at +420 703 614 444.",
}


async def handle_incoming(incoming: IncomingMessage) -> str:
    """Single entry point for all bots. Returns response text."""
    conversation = await core_api.get_or_create_conversation(
        client_id=incoming.client_id,
        channel=incoming.channel,
        client_name=incoming.client_name,
    )
    conversation_id = conversation.id

    await core_api.save_chat_message(
        conversation_id=conversation_id,
        role="user",
        content=incoming.text,
    )

    history = await core_api.get_chat_history(conversation_id=conversation_id, limit=10)

    config = {"configurable": {"thread_id": str(incoming.client_id)}}

    result = await graph.ainvoke(
        {
            "incoming": incoming,
            "conversation_history": history,
            "conversation_id": conversation_id,
        },
        config=config,
    )

    if isinstance(result, dict):
        response_text = result.get("response", "")
        detected_intent = result.get("intent", None)
        detected_lang = result.get("language", None)
    else:
        response_text = getattr(result, "response", "")
        detected_intent = getattr(result, "intent", None)
        detected_lang = getattr(result, "language", None)

    if not response_text:
        response_text = _EMPTY_RESPONSE_FALLBACK.get(detected_lang, _EMPTY_RESPONSE_FALLBACK["uk"])

    log_event(
        "response_sent",
        status="ok",
        response=response_text,
        intent=detected_intent,
        lang=detected_lang,
    )

    await core_api.save_chat_message(
        conversation_id=conversation_id,
        role="assistant",
        content=response_text,
        intent=detected_intent,
    )

    return response_text
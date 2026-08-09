from src.ai.conversation_agent.graph import graph
from src.schemas.ai.messages import IncomingMessage
from src.api_client.core_api import core_api


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
    else:
        response_text = getattr(result, "response", "")
        detected_intent = getattr(result, "intent", None)

    await core_api.save_chat_message(
        conversation_id=conversation_id,
        role="assistant",
        content=response_text,
        intent=detected_intent,
    )

    return response_text
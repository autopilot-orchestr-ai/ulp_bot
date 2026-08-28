from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
from langgraph.graph import END, StateGraph

from src.ai.conversation_agent.nodes.chat import chat_node
from src.ai.conversation_agent.nodes.gate import classify_lead_intent
from src.ai.conversation_agent.nodes.lead_capture import lead_capture_node
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.routing import route_after_gate, route_after_lead_capture
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("gate", classify_lead_intent)
    graph.add_node("chat", chat_node)
    graph.add_node("lead_capture", lead_capture_node)

    graph.set_entry_point("gate")

    graph.add_conditional_edges(
        "gate",
        route_after_gate,
        {
            Route.LEAD.value: "lead_capture",
            Route.CHAT.value: "chat",
        },
    )

    graph.add_conditional_edges(
        "lead_capture",
        route_after_lead_capture,
        {
            Route.CHAT.value: "chat",
            # NOT "lead_capture": see routing.py's route_after_lead_capture
            # docstring - that self-loop caused GraphRecursionError.
            Route.LEAD.value: END,
            Route.END.value: END,
        },
    )

    graph.add_edge("chat", END)

    # AgentState.incoming (IncomingMessage) and .route (Route) are custom
    # types stored in checkpointed state. Without an explicit allowlist,
    # langgraph's msgpack serde logs a deprecation warning on every
    # serialize/deserialize and will refuse them outright in a future
    # version - allowlist both now rather than waiting for that to break.
    memory = MemorySaver(
        serde=JsonPlusSerializer(allowed_msgpack_modules=[IncomingMessage, Route])
    )
    return graph.compile(checkpointer=memory)


graph = build_graph()


async def reset_thread_state(client_id: str) -> None:
    """Clears the LangGraph per-user state kept by the MemorySaver
    checkpointer (thread_id=client_id) - lead_step, current_service, and
    any collected contact fields. Used by /start (client-reported
    2026-08-28: they typed /start expecting a clean slate before testing a
    language switch, but /start was purely a cosmetic welcome message that
    touched no state at all - an abandoned lead form or a stale
    current_service would silently carry over into what should have been a
    fresh start).

    NOTE: this only clears in-process graph state. It does NOT clear
    conversation_history, which lives in the external Core API
    (src/api_client/core_api.py) and has no delete/reset endpoint - chat's
    LLM context still includes prior turns after /start. A true "wipe the
    visible chat history" reset would need a Core API change, out of scope
    for this repo.
    """
    config = {"configurable": {"thread_id": str(client_id)}}

    # Regression, verified 2026-08-28: aupdate_state only writes the
    # channels named in its dict - it never touches `incoming` (required,
    # no default on AgentState) since a reset has no message to put there.
    # For a thread with an existing checkpoint that's harmless (`incoming`
    # already holds a value from a real turn, untouched by this partial
    # write). But for a brand-new thread - genuinely the most common case
    # for /start: a new user, or any user right after a deploy restart
    # wipes this in-process MemorySaver - aupdate_state creates the FIRST
    # checkpoint for that thread with `incoming` never written at all. The
    # next real ainvoke() then merges its input onto that checkpoint rather
    # than treating it as a fresh full state, and crashes on `AgentState`
    # validation ("incoming: Field required") before the client's very
    # first message could be answered - confirmed via a local repro against
    # the real graph + MemorySaver, not just the production traceback.
    # Skip entirely when there's no existing checkpoint - a fresh thread
    # already starts at every field's proper default, nothing to reset.
    if not (await graph.aget_state(config)).values:
        return

    await graph.aupdate_state(
        config,
        {
            "lead_step": None,
            "current_service": None,
            "client_name": None,
            "client_phone": None,
            "client_email": None,
            "language": None,
        },
    )

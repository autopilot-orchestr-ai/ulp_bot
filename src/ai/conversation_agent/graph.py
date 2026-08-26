from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.ai.conversation_agent.nodes.chat import chat_node
from src.ai.conversation_agent.nodes.gate import classify_lead_intent
from src.ai.conversation_agent.nodes.lead_capture import lead_capture_node
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.routing import route_after_gate, route_after_lead_capture
from src.ai.conversation_agent.state import AgentState


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

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


graph = build_graph()

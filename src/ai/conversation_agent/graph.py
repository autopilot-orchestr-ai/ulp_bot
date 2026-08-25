from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.ai.conversation_agent.nodes.call_timing import call_timing_reply
from src.ai.conversation_agent.nodes.escalation import escalate
from src.ai.conversation_agent.nodes.info import info_agent
from src.ai.conversation_agent.nodes.lead_capture import lead_capture_node
from src.ai.conversation_agent.nodes.off_topic import off_topic_reply
from src.ai.conversation_agent.nodes.supervisor import classify_intent
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState


def _route_after_supervisor(state: AgentState) -> str:
    """Prioritizes active lead capture form over re-classification."""
    if state.lead_step is not None and state.lead_step != "completed":
        return Route.LEAD.value

    return state.route.value if hasattr(state.route, "value") else str(state.route)


def _route_after_lead_capture(state: AgentState) -> str:
    """Handles routing out of lead capture (e.g. mid-form questions)."""
    return state.route.value if hasattr(state.route, "value") else str(state.route)


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # Nodes
    graph.add_node("supervisor", classify_intent)
    graph.add_node("info", info_agent)
    graph.add_node("lead_capture", lead_capture_node)
    graph.add_node("escalation", escalate)
    graph.add_node("off_topic", off_topic_reply)
    graph.add_node("call_timing", call_timing_reply)

    # Entry point
    graph.set_entry_point("supervisor")

    # Supervisor routing
    graph.add_conditional_edges(
        "supervisor",
        _route_after_supervisor,
        {
            Route.INFO.value: "info",
            Route.LEAD.value: "lead_capture",
            Route.HUMAN.value: "escalation",
            Route.OFF_TOPIC.value: "off_topic",
            Route.CALL_TIMING.value: "call_timing",
        },
    )

    # Lead capture routing
    graph.add_conditional_edges(
        "lead_capture",
        _route_after_lead_capture,
        {
            Route.INFO.value: "info",
            Route.HUMAN.value: "escalation",
            Route.LEAD.value: "lead_capture",
            Route.END.value: END,
        },
    )

    # Terminal nodes
    for node in ("info", "escalation", "off_topic", "call_timing"):
        graph.add_edge(node, END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


graph = build_graph()
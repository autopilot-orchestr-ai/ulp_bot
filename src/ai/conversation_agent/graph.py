from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.nodes.supervisor import classify_intent
from src.ai.conversation_agent.nodes.answer_question import answer_question
from src.ai.conversation_agent.nodes.info import info_agent
from src.ai.conversation_agent.nodes.escalation import escalate
from src.ai.conversation_agent.nodes.off_topic import off_topic_reply
from src.ai.conversation_agent.nodes.lead_capture import lead_capture_node


def _route_intent(state: AgentState) -> str:
    if isinstance(state, dict):
        lead_step = state.get("lead_step")
        intent = state.get("intent", "")
    else:
        lead_step = getattr(state, "lead_step", None)
        intent = getattr(state, "intent", "")

    if lead_step and lead_step != "completed":
        return "lead_capture"

    intent = (intent or "").lower().strip()

    match intent:
        case (
            "faq"
            | "faq_intent"
            | "price_intent"
            | "pricing"
            | "services"
            | "general_question"
            | "document_intent"
            | "greeting"
        ):
            return "faq"

        case "info" | "info_intent" | "about_company":
            return "info"

        case "lead_intent" | "lead" | "booking" | "consultation":
            return "lead_capture"

        case "off_topic":
            return "off_topic"

        case _:
            return "escalation"


def _route_after_lead_capture(state: AgentState) -> str:
    """Перевіряє, чи поставив користувач запитання під час заповнення форми."""
    if isinstance(state, dict):
        route_to_llm = state.get("route_to_llm")
    else:
        route_to_llm = getattr(state, "route_to_llm", False)

    if route_to_llm:
        return "faq"
    return "end"


memory = MemorySaver()


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("supervisor", classify_intent)
    graph.add_node("faq", answer_question)
    graph.add_node("info", info_agent)
    graph.add_node("lead_capture", lead_capture_node)
    graph.add_node("escalation", escalate)
    graph.add_node("off_topic", off_topic_reply)

    graph.set_entry_point("supervisor")

    graph.add_conditional_edges(
        "supervisor",
        _route_intent,
        {
            "faq": "faq",
            "info": "info",
            "lead_capture": "lead_capture",
            "escalation": "escalation",
            "off_topic": "off_topic",
        },
    )

    graph.add_conditional_edges(
        "lead_capture",
        _route_after_lead_capture,
        {
            "faq": "faq",
            "end": END,
        },
    )

    graph.add_edge("faq", END)
    graph.add_edge("info", END)
    graph.add_edge("escalation", END)
    graph.add_edge("off_topic", END)

    return graph.compile(checkpointer=memory)


graph = build_graph()
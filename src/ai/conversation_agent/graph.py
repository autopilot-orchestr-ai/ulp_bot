from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.routes import Route

from src.ai.conversation_agent.nodes.supervisor import (
    classify_intent,
)
from src.ai.conversation_agent.nodes.info import (
    info_agent,
)
from src.ai.conversation_agent.nodes.escalation import (
    escalate,
)
from src.ai.conversation_agent.nodes.off_topic import (
    off_topic_reply,
)
from src.ai.conversation_agent.nodes.lead_capture import (
    lead_capture_node,
)
from src.ai.conversation_agent.nodes.call_timing import (
    call_timing_reply,
)


def _route_after_supervisor(
    state: AgentState,
) -> str:
    """
    Active lead form always has priority.

    This prevents the LLM supervisor from
    re-classifying form answers such as:

        "John Smith"
        "+420 777 123 456"
        "test@gmail.com"

    as normal info messages.
    """

    if (
        state.lead_step is not None
        and state.lead_step != "completed"
    ):
        return Route.LEAD.value

    return state.route.value


def _route_after_lead_capture(
    state: AgentState,
) -> str:
    """
    Lead capture can temporarily hand the
    conversation to another node when the
    user asks a question while filling the form.
    """

    return state.route.value


memory = MemorySaver()


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    # ---------------------------------------------------------
    # NODES
    # ---------------------------------------------------------

    graph.add_node(
        "supervisor",
        classify_intent,
    )

    graph.add_node(
        "info",
        info_agent,
    )

    graph.add_node(
        "lead_capture",
        lead_capture_node,
    )

    graph.add_node(
        "escalation",
        escalate,
    )

    graph.add_node(
        "off_topic",
        off_topic_reply,
    )

    graph.add_node(
        "call_timing",
        call_timing_reply,
    )

    # ---------------------------------------------------------
    # START
    # ---------------------------------------------------------

    graph.set_entry_point("supervisor")

    # ---------------------------------------------------------
    # SUPERVISOR → NODE
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # LEAD CAPTURE → NODE
    # ---------------------------------------------------------

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

    # ---------------------------------------------------------
    # TERMINAL NODES
    # ---------------------------------------------------------

    graph.add_edge(
        "info",
        END,
    )

    graph.add_edge(
        "escalation",
        END,
    )

    graph.add_edge(
        "off_topic",
        END,
    )

    graph.add_edge(
        "call_timing",
        END,
    )

    return graph.compile(
        checkpointer=memory
    )


graph = build_graph()
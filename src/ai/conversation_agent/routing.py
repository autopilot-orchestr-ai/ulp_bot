"""Pure routing functions for the conversation graph (src/ai/conversation_agent/graph.py).

Kept separate from graph.py so they're testable without constructing (or
mocking) the actual LangGraph StateGraph / node functions.
"""
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState


def route_after_gate(state: AgentState) -> str:
    """An in-progress lead form always takes priority over the gate's fresh
    classification for this turn (gate.py itself already skips the LLM
    classification call entirely in that case)."""
    if state.lead_step is not None and state.lead_step != "completed":
        return Route.LEAD.value
    return state.route.value if hasattr(state.route, "value") else str(state.route)


def route_after_lead_capture(state: AgentState) -> str:
    """lead_capture can hand off to `chat` mid-form (the user asked a
    question instead of answering) or end the turn. Route.LEAD must map to
    END in the graph's edge table, not back to "lead_capture" - looping
    within one invocation replays the same already-consumed message against
    the next/unchanged step forever, which is what caused the
    GraphRecursionError loop fixed on 2026-08-26. Cross-turn continuation of
    an active form is handled separately by route_after_gate, above."""
    return state.route.value if hasattr(state.route, "value") else str(state.route)

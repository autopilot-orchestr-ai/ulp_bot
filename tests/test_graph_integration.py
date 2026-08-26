# tests/test_graph_integration.py
from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.routes import Route
from src.schemas.ai.messages import IncomingMessage


def _incoming(text):
    return IncomingMessage(
        client_id="graph-test", channel="telegram", text=text,
        timestamp=datetime.now(), client_name="Test",
    )


async def _invoke_with_stubs(thread_id, payload, *, gate_return, chat_return=None, lead_return=None):
    with patch(
        "src.ai.conversation_agent.graph.classify_lead_intent",
        new_callable=AsyncMock, return_value=gate_return,
    ), patch(
        "src.ai.conversation_agent.graph.chat_node",
        new_callable=AsyncMock, return_value=chat_return or {"response": "chat stub"},
    ), patch(
        "src.ai.conversation_agent.graph.lead_capture_node",
        new_callable=AsyncMock, return_value=lead_return or {"response": "lead stub", "route": Route.END},
    ):
        from src.ai.conversation_agent.graph import build_graph
        graph = build_graph()
        return await graph.ainvoke(payload, config={"configurable": {"thread_id": thread_id}})


async def test_fresh_message_wants_lead_routes_to_lead_capture():
    result = await _invoke_with_stubs(
        "t1",
        {"incoming": _incoming("Зателефонуйте мені")},
        gate_return={"intent": "lead", "route": Route.LEAD, "language": "uk"},
    )
    assert result["response"] == "lead stub"


async def test_fresh_message_no_lead_intent_routes_to_chat():
    result = await _invoke_with_stubs(
        "t2",
        {"incoming": _incoming("Скільки коштує апостиль?")},
        gate_return={"intent": "chat", "route": Route.CHAT, "language": "uk"},
    )
    assert result["response"] == "chat stub"


async def test_active_lead_form_skips_gate_classification_result():
    """Even if the gate stub says CHAT, an in-progress form must win."""
    result = await _invoke_with_stubs(
        "t3",
        {"incoming": _incoming("+420 777 123 456"), "lead_step": "awaiting_phone"},
        gate_return={"intent": "chat", "route": Route.CHAT, "language": "uk"},
        lead_return={"response": "phone captured", "lead_step": "awaiting_email", "route": Route.END},
    )
    assert result["response"] == "phone captured"


async def test_lead_capture_can_hand_off_to_chat_mid_form():
    result = await _invoke_with_stubs(
        "t4",
        {"incoming": _incoming("what are your working hours?"), "lead_step": "awaiting_name"},
        gate_return={"intent": "chat", "route": Route.CHAT, "language": "uk"},
        lead_return={"route": Route.CHAT},
        chat_return={"response": "8 to 5, Mon-Fri"},
    )
    assert result["response"] == "8 to 5, Mon-Fri"


async def test_lead_capture_route_lead_terminates_the_turn_not_loops():
    """Regression test for the GraphRecursionError bug fixed 2026-08-26:
    lead_capture returning Route.LEAD (the default outcome for a reprompt or
    a step advance) must end the turn, not re-invoke lead_capture again in
    the same graph run. Reverting graph.py's Route.LEAD.value target back to
    "lead_capture" must make this test fail."""
    result = await _invoke_with_stubs(
        "t5",
        {"incoming": _incoming("Іван Петренко"), "lead_step": "awaiting_name"},
        gate_return={"intent": "lead", "route": Route.LEAD, "language": "uk"},
        lead_return={"response": "what is your phone?", "lead_step": "awaiting_phone", "route": Route.LEAD},
    )
    assert result["response"] == "what is your phone?"

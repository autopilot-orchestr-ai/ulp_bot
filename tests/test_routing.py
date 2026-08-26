from datetime import datetime

from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.routing import route_after_gate, route_after_lead_capture
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def _state(lead_step=None, route=Route.END):
    incoming = IncomingMessage(
        client_id="1", channel="telegram", text="hi",
        timestamp=datetime.now(), client_name="Test",
    )
    return AgentState(incoming=incoming, lead_step=lead_step, route=route)


def test_gate_routing_prioritizes_active_lead_form_over_fresh_route():
    state = _state(lead_step="awaiting_phone", route=Route.CHAT)
    assert route_after_gate(state) == Route.LEAD.value


def test_gate_routing_ignores_completed_lead_step():
    state = _state(lead_step="completed", route=Route.CHAT)
    assert route_after_gate(state) == Route.CHAT.value


def test_gate_routing_uses_state_route_when_no_active_form():
    state = _state(lead_step=None, route=Route.LEAD)
    assert route_after_gate(state) == Route.LEAD.value


def test_lead_capture_routing_returns_state_route_value():
    assert route_after_lead_capture(_state(route=Route.CHAT)) == Route.CHAT.value
    assert route_after_lead_capture(_state(route=Route.END)) == Route.END.value
    assert route_after_lead_capture(_state(route=Route.LEAD)) == Route.LEAD.value

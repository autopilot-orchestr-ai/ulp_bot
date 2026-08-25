import uuid
from typing import Any, Literal, Optional
from pydantic import BaseModel, Field
from src.schemas.ai.messages import IncomingMessage


class BaseState(BaseModel):
    incoming: IncomingMessage
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    response: str = ""
    conversation_id: uuid.UUID | None = None

    client_name: str | None = None
    client_phone: str | None = None
    client_email: str | None = None
    lead_step: Literal["awaiting_service", "awaiting_name", "awaiting_phone", "awaiting_email", "completed"] | None = None


class AgentState(BaseState):
    """Main graph state shared across all nodes."""
    language: Optional[str] = "uk"
    intent: str = ""
    current_service: str | None = None
    route_to_llm: bool = False
    retrieved_context: str | None = None


class ConversationState(BaseState):
    """State for conversation/FAQ nodes."""
    intent: str = ""
import uuid
from typing import Annotated, Any, Literal, Optional
from pydantic import BaseModel, Field
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

from src.schemas.ai.messages import IncomingMessage
from src.ai.conversation_agent.routes import Route


class BaseState(BaseModel):
    incoming: IncomingMessage
    # Added the messages field required by LangGraph/LangChain nodes
    messages: Annotated[list[BaseMessage], add_messages] = Field(default_factory=list)
    conversation_history: list[dict[str, Any]] = Field(default_factory=list)
    response: str = ""
    conversation_id: uuid.UUID | None = None

    client_name: str | None = None
    client_phone: str | None = None
    client_email: str | None = None
    lead_step: Literal["awaiting_service", "awaiting_consultation_type", "awaiting_contact_confirmation", "awaiting_name", "awaiting_phone", "awaiting_email", "completed"] | None = None


class AgentState(BaseState):
    """Main graph state shared across all nodes."""
    language: Optional[str] = "uk"
    intent: str = ""
    route: Route = Route.END
    current_service: str | None = None
    retrieved_context: str | None = None
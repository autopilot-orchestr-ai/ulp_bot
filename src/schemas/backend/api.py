from uuid import UUID
from pydantic import BaseModel, Field


class ConversationCreate(BaseModel):
    client_id: str
    channel: str
    client_name: str | None = None


class ConversationResponse(BaseModel):
    id: UUID
    client_id: str
    channel: str
    client_name: str | None = None


class MessageCreate(BaseModel):
    conversation_id: UUID
    role: str
    content: str
    intent: str | None = None


class ChatMessageSchema(BaseModel):
    role: str
    content: str


class UnansweredQuestionCreate(BaseModel):
    conversation_id: UUID
    question_text: str
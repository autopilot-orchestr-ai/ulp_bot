import httpx
from uuid import UUID
from src.config import settings
from src.schemas.backend.api import (
    ConversationCreate,
    ConversationResponse,
    MessageCreate,
    ChatMessageSchema,
    UnansweredQuestionCreate,
)


class CoreAPIClient:
    def __init__(self):
        # Отримуємо URL з конфігу (наприклад, http://admin_api:8000)
        self.base_url = settings.core_api_url.rstrip("/")

    async def get_or_create_conversation(
        self, client_id: str, channel: str, client_name: str | None = None
    ) -> ConversationResponse:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = ConversationCreate(
                client_id=client_id,
                channel=channel,
                client_name=client_name,
            ).model_dump(mode="json")
            
            response = await client.post(
                f"{self.base_url}/internal/bots/conversations", 
                json=payload
            )
            response.raise_for_status()
            return ConversationResponse.model_validate(response.json())

    async def save_chat_message(
        self, conversation_id: UUID, role: str, content: str, intent: str | None = None
    ) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = MessageCreate(
                conversation_id=conversation_id,
                role=role,
                content=content,
                intent=intent,
            ).model_dump(mode="json")
            
            response = await client.post(
                f"{self.base_url}/internal/bots/messages", 
                json=payload
            )
            response.raise_for_status()

    async def get_chat_history(
        self, conversation_id: UUID, limit: int = 10
    ) -> list[dict[str, str]]:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{self.base_url}/internal/bots/conversations/{conversation_id}/history",
                params={"limit": limit},
            )
            response.raise_for_status()
            return response.json()

    async def store_unanswered_question(
        self, conversation_id: UUID, question_text: str
    ) -> None:
        async with httpx.AsyncClient(timeout=10.0) as client:
            payload = UnansweredQuestionCreate(
                conversation_id=conversation_id,
                question_text=question_text,
            ).model_dump(mode="json")
            
            response = await client.post(
                f"{self.base_url}/internal/bots/unanswered", 
                json=payload
            )
            response.raise_for_status()


core_api = CoreAPIClient()
from functools import lru_cache
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, BaseMessage

from src.ai.conversation_agent.state import ConversationState
from src.ai.conversation_agent.prompts.conversation import SYSTEM_PROMPT as FAQ_SYSTEM_PROMPT
from src.ai.knowledge.store import KnowledgeStore
from src.ai.knowledge.llm import get_llm
from src.ai.knowledge.embeddings import get_embeddings
from src.ai.conversation_agent.data.lang import detect_lang
from src.config import settings
from src.logger import log_event


# ✅ cached — created once, reused on every call
@lru_cache(maxsize=1)
def _get_store() -> KnowledgeStore:
    return KnowledgeStore(
        db_url=settings.db_url,
        schema=settings.db_schema,
        embeddings=get_embeddings(
            settings.embeddings_model
        ),
    )


@lru_cache(maxsize=1)
def _get_llm():
    return get_llm(settings.llm_model)


def _build_messages(
    context: str,
    client_name: str,
    conversation_history: list[dict],
    incoming_text: str,
) -> list[BaseMessage]:
    """Build the message list to send to the LLM."""
    messages: list[BaseMessage] = [
        SystemMessage(content=FAQ_SYSTEM_PROMPT.format(
            client_name=client_name,
            context=context,
        ))
    ]

    for entry in conversation_history:
        cls = HumanMessage if entry["role"] == "user" else AIMessage
        messages.append(cls(content=entry["content"]))

    messages.append(HumanMessage(content=incoming_text))
    return messages


async def _retrieve_context(query: str, lang: str) -> str:
    """Retrieve relevant documents from the knowledge base."""
    store = _get_store()

    log_event("kb_retrieving", status="start", query=query, lang=lang)
    try:
        docs = await store.search(
            query=query,
            k=settings.retrieval_k,
            threshold=settings.similarity_threshold,
            filter={"lang": lang}
        )
        context = "\n\n".join(doc.page_content for doc in docs) if docs else "No specific information found."
        log_event("kb_retrieved", status="ok", chunks=len(docs))
        return context
    except Exception as exc:
        log_event("kb_retrieved", status="error", error=str(exc))
        raise


async def answer_question(state: ConversationState) -> dict:
    incoming_text = state.incoming.text

    lang = detect_lang(incoming_text)

    context = await _retrieve_context(incoming_text, lang)

    messages = _build_messages(
        context=context,
        client_name=settings.client_name,
        conversation_history=state.conversation_history,
        incoming_text=incoming_text,
    )

    llm = _get_llm()
    log_event("llm_calling", status="start", model=settings.llm_model)
    try:
        result = await llm.ainvoke(messages)
        log_event("llm_response", status="ok", text=result.content)
        return {"response": result.content}
    except Exception as exc:
        log_event("llm_response", status="error", error=str(exc))
        raise
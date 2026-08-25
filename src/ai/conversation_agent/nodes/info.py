from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.config import settings
from src.ai.conversation_agent.state import AgentState
from src.ai.knowledge.llm import get_llm
from src.ai.conversation_agent.prompts.info import INFO_SYSTEM_PROMPT
from src.bots.utils.language_detection import detect_lang
from src.logger import log_event
from src.ai.knowledge.store import KnowledgeStore
from src.ai.conversation_agent.routes import Route

knowledge_store = KnowledgeStore(settings.db_url, settings.db_schema, settings.embeddings_model)

async def info_agent(state: AgentState) -> dict:
    log_event(
        "info_agent_start",
        status="start",
        text=state.incoming.text,
    )

    lang = (
        detect_lang(state.incoming.text)
        or state.language
        or "en"
    )

    llm = get_llm(settings.llm_model)

    # 1. Search knowledge base
    documents = await knowledge_store.search(
        query=state.incoming.text,
        k=5,
        threshold=0.7,
    )

    # 2. Build context
    context = "\n\n".join(
        doc.page_content
        for doc in documents
    )

    # 3. Conversation history
    history_messages = []

    for m in state.conversation_history[-8:]:
        if m["role"] == "user":
            history_messages.append(
                HumanMessage(content=m["content"])
            )
        else:
            history_messages.append(
                AIMessage(content=m["content"])
            )

    # 4. Prompt
    system_instruction = f"""
You are the official assistant of United Legal Partners.

Answer ONLY using the provided knowledge base.

Language: {lang}

Knowledge base:
{context}

Rules:
- Do not invent prices.
- Do not invent services.
- Do not invent deadlines.
- If the information is missing, say that the manager should clarify it.
"""

    response = await llm.ainvoke([
        SystemMessage(content=system_instruction),
        *history_messages,
        HumanMessage(content=state.incoming.text),
    ])

    return {
        "response": response.content,
        "retrieved_context": context,
        "route": Route.END,
    }
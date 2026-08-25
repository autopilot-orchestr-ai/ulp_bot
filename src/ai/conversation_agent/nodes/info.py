from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.config import settings
from src.ai.conversation_agent.state import AgentState
from src.ai.knowledge.llm import get_llm
from src.ai.conversation_agent.prompts.info import INFO_SYSTEM_PROMPT
from src.bots.utils.language_detection import detect_lang
from src.logger import log_event
from src.ai.knowledge.store import KnowledgeStore
from src.ai.conversation_agent.routes import Route
from src.ai.knowledge.embeddings import get_embeddings

# Properly initialize KnowledgeStore with the Embeddings instance
knowledge_store = KnowledgeStore(
    db_url=settings.db_url,
    schema=settings.db_schema,
    embeddings=get_embeddings(settings.embeddings_model),
)


async def info_agent(state: AgentState) -> dict:
    """Handles general information queries using context vector retrieval."""
    # Change line 23 from state.messages to state["messages"]
    user_message = state["messages"][-1].content
    log_event("info_agent_start", text=user_message)

    # Increased k to 10 so all legal service entries are fetched
    docs = await knowledge_store.vectorstore.asimilarity_search(user_message, k=10)
    context = "\n\n".join([doc.page_content for doc in docs])

    system_prompt = INFO_SYSTEM_PROMPT.format(context=context)
    llm = get_llm()

    messages = [
        SystemMessage(content=system_prompt),
        *state.messages,
    ]

    response = await llm.ainvoke(messages)

    return {
        "messages": [response],
        "next_route": Route.END,
    }
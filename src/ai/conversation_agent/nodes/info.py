from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.config import settings
from src.ai.conversation_agent.state import AgentState
from src.ai.knowledge.llm import get_llm
from src.ai.conversation_agent.prompts.info import INFO_SYSTEM_PROMPT
from src.ai.conversation_agent.agent_rules.lang import detect_lang
from src.logger import log_event

async def info_agent(state: AgentState) -> dict:
    log_event("info_agent_start", status="start", text=state.incoming.text)
    
    lang = detect_lang(state.incoming.text) or getattr(state, "language", None) or "en"
    llm = get_llm(settings.llm_model)

    history_messages = []
    for m in state.conversation_history[-8:]:
        if m["role"] == "user":
            history_messages.append(HumanMessage(content=m["content"]))
        else:
            history_messages.append(AIMessage(content=m["content"]))

    system_instruction = INFO_SYSTEM_PROMPT.format(lang=lang)

    try:
        response = await llm.ainvoke([
            SystemMessage(content=system_instruction),
            *history_messages,
            HumanMessage(content=state.incoming.text)
        ])
        
        log_event("info_agent_finished", status="ok")
        return {"response": response.content}

    except Exception as exc:
        log_event("info_agent_error", status="error", error=str(exc))
        raise
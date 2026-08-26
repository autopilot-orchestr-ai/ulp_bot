import uuid
from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.tools.chat_tools import build_log_unanswered_question_tool


async def test_log_unanswered_question_uses_the_real_conversation_id():
    conversation_id = uuid.uuid4()
    tool = build_log_unanswered_question_tool(conversation_id=conversation_id)
    with patch(
        "src.ai.conversation_agent.tools.chat_tools.core_api"
    ) as mock_core_api:
        mock_core_api.store_unanswered_question = AsyncMock()
        result = await tool.ainvoke({"question": "Can I get a refund?"})
    mock_core_api.store_unanswered_question.assert_awaited_once_with(
        conversation_id=conversation_id, question_text="Can I get a refund?"
    )
    assert result == "logged"


async def test_log_unanswered_question_swallows_db_errors():
    tool = build_log_unanswered_question_tool(conversation_id=uuid.uuid4())
    with patch(
        "src.ai.conversation_agent.tools.chat_tools.core_api"
    ) as mock_core_api:
        mock_core_api.store_unanswered_question = AsyncMock(
            side_effect=RuntimeError("db down")
        )
        result = await tool.ainvoke({"question": "..."})  # must not raise
    assert result == "logged"

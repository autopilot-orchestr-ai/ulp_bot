# tests/test_chat.py
import uuid
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.messages import AIMessage

from src.ai.conversation_agent.nodes.chat import chat_node
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def _state(text, language="uk", conversation_id=None):
    incoming = IncomingMessage(
        client_id="1", channel="telegram", text=text,
        timestamp=datetime.now(), client_name="Test",
    )
    return AgentState(
        incoming=incoming,
        language=language,
        conversation_id=conversation_id or uuid.uuid4(),
    )


def _fake_llm(ai_message):
    llm = MagicMock()
    llm.bind_tools.return_value = llm
    llm.ainvoke = AsyncMock(return_value=ai_message)
    return llm


async def test_chat_replies_directly_when_no_tool_called(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("## English (en)\nWe offer legal consultations.", encoding="utf-8")
    reply = AIMessage(content="Привіт! Чим можу допомогти?", tool_calls=[])
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm", return_value=_fake_llm(reply)
    ), patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        result = await chat_node(_state("Привіт"))
    assert result == {"response": "Привіт! Чим можу допомогти?"}


async def test_chat_reads_company_info_file_into_the_prompt(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("UNIQUE_MARKER_12345", encoding="utf-8")
    reply = AIMessage(content="ok", tool_calls=[])
    fake_llm = _fake_llm(reply)
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm", return_value=fake_llm
    ), patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        await chat_node(_state("hello", language="en"))
    sent_messages = fake_llm.ainvoke.call_args[0][0]
    system_message = sent_messages[0]
    assert "UNIQUE_MARKER_12345" in system_message.content


async def test_chat_short_circuits_to_handoff_message_on_log_unanswered_question(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("## English (en)\nWe offer legal consultations.", encoding="utf-8")
    tool_call = AIMessage(
        content="",
        tool_calls=[{"name": "log_unanswered_question", "args": {"question": "custody advice"}, "id": "call_1"}],
    )
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm", return_value=_fake_llm(tool_call)
    ), patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings, patch(
        "src.ai.conversation_agent.nodes.chat.build_log_unanswered_question_tool"
    ) as build_log_tool:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        fake_tool = MagicMock()
        fake_tool.name = "log_unanswered_question"
        fake_tool.ainvoke = AsyncMock(return_value="logged")
        build_log_tool.return_value = fake_tool
        result = await chat_node(_state("What should I do about custody?", language="en"))
    fake_tool.ainvoke.assert_awaited_once_with({"question": "custody advice"})
    assert "office@ak-ulp.cz" in result["response"]


async def test_chat_call_timing_fast_path_skips_llm(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("## English (en)\nWe offer legal consultations.", encoding="utf-8")
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm"
    ) as get_llm, patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        result = await chat_node(_state("коли ви зателефонуєте?", language="uk"))
    get_llm.assert_not_called()
    assert "8:00" in result["response"] and "17:00" in result["response"]


async def test_chat_call_timing_fast_path_prepends_weekend_notice(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("## English (en)\nWe offer legal consultations.", encoding="utf-8")
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm"
    ), patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        result = await chat_node(_state("коли ви зателефонуєте мені в суботу?", language="uk"))
    assert "вихідн" in result["response"].lower()
    assert "8:00" in result["response"]


async def test_chat_non_call_timing_message_still_uses_llm(tmp_path):
    info_file = tmp_path / "company_info.md"
    info_file.write_text("## English (en)\nWe offer legal consultations.", encoding="utf-8")
    reply = AIMessage(content="hi there", tool_calls=[])
    with patch(
        "src.ai.conversation_agent.nodes.chat.get_llm", return_value=_fake_llm(reply)
    ), patch(
        "src.ai.conversation_agent.nodes.chat.settings"
    ) as mock_settings:
        mock_settings.company_info_path = str(info_file)
        mock_settings.llm_model = "gpt-4o-mini"
        result = await chat_node(_state("Привіт", language="uk"))
    assert result == {"response": "hi there"}

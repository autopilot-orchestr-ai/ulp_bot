# Conversational Graph Refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current 6-node LangGraph pipeline (`supervisor` → `info`/`lead_capture`/`escalation`/`off_topic`/`call_timing`) with a 3-node pipeline (`gate` → `chat`/`lead_capture`), and consolidate every scrap of company info (services, pricing, required documents, contact/office/hours, FAQ) — today scattered across a hardcoded prompt block, a separate FAQ YAML never actually loaded into the DB, and a pgvector pipeline that's dead weight — into one single Markdown file the `chat` node reads fresh on every turn, so an edit takes effect on the very next message with no reload or restart.

**Architecture:** `gate` (binary "does this message show clear commitment to proceed or an explicit request for a human?" classifier, replaces the old 5-way `supervisor`) routes either into the unchanged `lead_capture` state machine or into `chat` — one LLM node that reads `src/assets/company_info.md` on every call and injects its full contents into the system prompt (no retrieval, no embeddings, no vector DB), bound to a single `log_unanswered_question` tool for questions that genuinely aren't covered by the file.

**Tech Stack:** langgraph, langchain-core (`@tool`, `.bind_tools()`, `.with_structured_output()`), langchain-openai, pytest + pytest-asyncio (new dev dependencies — this repo currently has no test suite at all).

## Global Constraints

- `lead_capture.py`'s state machine (service → name → phone → email, regex + LLM field validation) is NOT to be touched behaviorally — only its 3 `Route.INFO` references get renamed to `Route.CHAT` (Task 7), a pure rename with zero behavior change.
- The `gate` node drops the LLM-based `service_name` extraction the old `supervisor.py` did. This is safe, not a regression: `lead_capture._step_start` already falls back to `FormValidator.detect_service(state.incoming.text)` (regex, same raw text) whenever `current_service` isn't pre-set, and that fallback is exercised in production today whenever the old classifier didn't find a service either.
- **Single source of truth for company info, confirmed with the user:** `src/assets/company_info.md` — one Markdown file, one section per language (uk/cs/en/ru), covering identity, contact/office/hours, the full services+pricing+required-documents list, and FAQ. `chat_node` reads it from disk on every call (no caching, no ingestion step) and injects the whole file into the system prompt. This replaces both the hardcoded `INFO_SYSTEM_PROMPT` block and `src/assets/faq.yaml` — do not leave the old content duplicated anywhere.
- **The pgvector knowledge pipeline is retired, confirmed with the user** (it was already non-functional: `load_faq()` was never called from anywhere in the codebase, so the KB was very likely always empty in production). `KnowledgeStore`, `embeddings.py`, `faq_loader.py`, `faq.yaml`, the `langchain-postgres` dependency, and the now-unused `db_url`/`db_schema`/`embeddings_provider`/`embeddings_model`/`faq_path`/`website_url`/`context_window`/`retrieval_k`/`similarity_threshold` Settings fields are all deleted in Task 8. `src/ai/knowledge/llm.py` (a generic `ChatOpenAI` factory, unrelated to the KB despite its location) survives, moved to `src/ai/llm.py` since `ai/knowledge/` would otherwise be an empty, misleadingly-named directory holding one unrelated file.
- **Known tradeoff, called out rather than hidden:** company info lives in 4 parallel per-language sections in one file, not one canonical language the LLM translates on the fly. This mirrors the structure `faq.yaml` already used (the firm evidently wants controlled, pre-approved wording per language, not live LLM translation of legal-service terms) — but it does mean the same fact (e.g. a price change) must be updated in up to 4 places *within that one file*, not 4 files. Whole-file injection on every turn also costs somewhat more tokens per message than the old hardcoded-English-only prompt did; given the file's size (~700 lines across 4 languages) this is a deliberate simplicity-over-optimization tradeoff, not an oversight.
- No test framework exists yet (`grep` confirms zero pytest/unittest usage repo-wide). Task 1 adds `pytest` + `pytest-asyncio` as dev dependencies and a `tests/conftest.py` that stubs every required-with-no-default `Settings` field via `os.environ.setdefault(...)`, because `src.config.Settings()` is instantiated at import time and half of `src/` transitively imports it — without this, no test file can even be collected. Task 8 trims this stub list once the KB-only Settings fields are removed.
- Node modules must not perform network I/O (DB connections, LLM client construction) at **import** time — only inside the node's async function body. This is required so `import src.ai.conversation_agent.graph` stays safe in tests without a live OpenAI connection.

---

### Task 1: Test infrastructure

**Files:**
- Modify: `pyproject.toml`
- Create: `tests/conftest.py`

**Interfaces:**
- Produces: every later task's tests run via `poetry run pytest tests/<file>.py -v`; async `def test_*` functions need no `@pytest.mark.asyncio` decorator (`asyncio_mode = "auto"`).

- [ ] **Step 1: Add pytest dependencies and config to `pyproject.toml`**

Add this block after `[tool.poetry.dependencies]`'s closing (before `[build-system]`):

```toml
[tool.poetry.group.dev.dependencies]
pytest = "^8.3.0"
pytest-asyncio = "^0.24.0"

[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["tests"]
```

- [ ] **Step 2: Install**

Run: `poetry install`

- [ ] **Step 3: Write `tests/conftest.py`**

```python
"""Stubs every Settings field that has no default, so `src.config.Settings()`
(instantiated at import time by nearly everything under src/) doesn't raise
a pydantic ValidationError when tests import project modules without a real
.env file. Pydantic-settings matches env var names case-insensitively, so
uppercase here matches the lowercase field names in src/config.py.

NOTE: this list matches src/config.py as of Task 1. Task 8 removes the
KB-only fields (db_url, db_schema, embeddings_provider, embeddings_model,
faq_path, website_url, context_window, retrieval_k, similarity_threshold)
from Settings and must trim this dict to match, or every test will start
failing to import with "extra fields not permitted"... actually pydantic-
settings ignores unknown env vars by default (extra="ignore" is set in
Settings.model_config), so a stale stub here just becomes inert - but keep
it trimmed anyway so this file documents what's actually required."""
import os

_TEST_ENV = {
    "CLIENT_NAME": "Test Client",
    "TELEGRAM_BOT_TOKEN": "test-token",
    "DB_URL": "postgresql+asyncpg://test:test@localhost:5432/test",
    "DB_SCHEMA": "test",
    "LLM_PROVIDER": "openai",
    "LLM_MODEL": "gpt-4o-mini",
    "OPENAI_API_KEY": "test-key",
    "EMBEDDINGS_PROVIDER": "openai",
    "EMBEDDINGS_MODEL": "text-embedding-3-small",
    "FAQ_PATH": "faq.yaml",
    "WEBSITE_URL": "https://example.com",
    "CONTEXT_WINDOW": "4000",
    "RETRIEVAL_K": "5",
    "SIMILARITY_THRESHOLD": "0.7",
    "GOOGLE_CALENDAR_ID": "test-calendar",
    "GOOGLE_SERVICE_ACCOUNT_JSON": "{}",
    "BOOKING_DAYS_AHEAD": "14",
    "BOOKING_MAX_SLOTS": "5",
    "BOOKING_SLOT_DURATION_MINUTES": "30",
    "BOOKING_WORKING_HOURS_START": "08:00",
    "BOOKING_WORKING_HOURS_END": "17:00",
    "BOOKING_WORKING_DAYS": "MON,TUE,WED,THU,FRI",
    "SMTP_HOST": "localhost",
    "SMTP_PORT": "587",
    "SMTP_USER": "test",
    "SMTP_PASSWORD": "test",
    "SMTP_FROM": "test@example.com",
}

for _key, _value in _TEST_ENV.items():
    os.environ.setdefault(_key, _value)
```

- [ ] **Step 4: Verify collection works with no tests yet**

Run: `poetry run pytest --collect-only`
Expected: exits 0, "no tests ran" (no test files exist yet — this just proves `conftest.py` imports cleanly and `src.config` doesn't blow up).

- [ ] **Step 5: Commit**

```bash
git add pyproject.toml tests/conftest.py
git commit -m "test: add pytest infra and Settings env stubs for testability"
```

---

### Task 2: `Route.CHAT` + pure routing functions

**Files:**
- Modify: `src/ai/conversation_agent/routes.py`
- Create: `src/ai/conversation_agent/routing.py`
- Test: `tests/test_routing.py`

**Interfaces:**
- Consumes: `AgentState` (`src/ai/conversation_agent/state.py`, unchanged), `Route` enum.
- Produces: `Route.CHAT` enum member; `route_after_gate(state) -> str`, `route_after_lead_capture(state) -> str` — both consumed by `graph.py` in Task 7.

This is purely additive — `Route.CHAT` is a new member alongside the existing ones (`INFO`, `HUMAN`, `OFF_TOPIC`, `CALL_TIMING` are removed later, in Task 8, once nothing references them). Nothing existing breaks.

- [ ] **Step 1: Write the failing test**

```python
# tests/test_routing.py
from datetime import datetime

from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.routing import route_after_gate, route_after_lead_capture
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def _state(lead_step=None, route=Route.END):
    incoming = IncomingMessage(
        client_id="1", channel="telegram", text="hi",
        timestamp=datetime.now(), client_name="Test",
    )
    return AgentState(incoming=incoming, lead_step=lead_step, route=route)


def test_gate_routing_prioritizes_active_lead_form_over_fresh_route():
    state = _state(lead_step="awaiting_phone", route=Route.CHAT)
    assert route_after_gate(state) == Route.LEAD.value


def test_gate_routing_ignores_completed_lead_step():
    state = _state(lead_step="completed", route=Route.CHAT)
    assert route_after_gate(state) == Route.CHAT.value


def test_gate_routing_uses_state_route_when_no_active_form():
    state = _state(lead_step=None, route=Route.LEAD)
    assert route_after_gate(state) == Route.LEAD.value


def test_lead_capture_routing_returns_state_route_value():
    assert route_after_lead_capture(_state(route=Route.CHAT)) == Route.CHAT.value
    assert route_after_lead_capture(_state(route=Route.END)) == Route.END.value
    assert route_after_lead_capture(_state(route=Route.LEAD)) == Route.LEAD.value
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_routing.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ai.conversation_agent.routing'` and `ImportError: cannot import name 'CHAT' from 'src.ai.conversation_agent.routes'`.

- [ ] **Step 3: Add `Route.CHAT` to `routes.py`**

In `src/ai/conversation_agent/routes.py`, add one line to the existing enum (don't remove any members yet):

```python
class Route(str, Enum):
    END = "end"
    INFO = "info"
    LEAD = "lead"
    HUMAN = "human"
    OFF_TOPIC = "off_topic"
    CALL_TIMING = "call_timing"
    CHAT = "chat"
```

- [ ] **Step 4: Write `src/ai/conversation_agent/routing.py`**

```python
"""Pure routing functions for the conversation graph (src/ai/conversation_agent/graph.py).

Kept separate from graph.py so they're testable without constructing (or
mocking) the actual LangGraph StateGraph / node functions.
"""
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState


def route_after_gate(state: AgentState) -> str:
    """An in-progress lead form always takes priority over the gate's fresh
    classification for this turn (gate.py itself already skips the LLM
    classification call entirely in that case)."""
    if state.lead_step is not None and state.lead_step != "completed":
        return Route.LEAD.value
    return state.route.value if hasattr(state.route, "value") else str(state.route)


def route_after_lead_capture(state: AgentState) -> str:
    """lead_capture can hand off to `chat` mid-form (the user asked a
    question instead of answering) or end the turn. Route.LEAD must map to
    END in the graph's edge table, not back to "lead_capture" - looping
    within one invocation replays the same already-consumed message against
    the next/unchanged step forever, which is what caused the
    GraphRecursionError loop fixed on 2026-08-26. Cross-turn continuation of
    an active form is handled separately by route_after_gate, above."""
    return state.route.value if hasattr(state.route, "value") else str(state.route)
```

- [ ] **Step 5: Run test to verify it passes**

Run: `poetry run pytest tests/test_routing.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Commit**

```bash
git add src/ai/conversation_agent/routes.py src/ai/conversation_agent/routing.py tests/test_routing.py
git commit -m "feat: add Route.CHAT and standalone routing functions"
```

---

### Task 3: `log_unanswered_question` tool

**Files:**
- Create: `src/ai/conversation_agent/tools/chat_tools.py`
- Test: `tests/test_chat_tools.py`

**Interfaces:**
- Consumes: `core_api` (`src/api_client/core_api.py`, unchanged — `async def store_unanswered_question(conversation_id, question_text) -> None`).
- Produces: `build_log_unanswered_question_tool(conversation_id: UUID) -> BaseTool` (tool name `"log_unanswered_question"`, one arg `question: str`) — consumed by `nodes/chat.py` in Task 6.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_chat_tools.py
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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `poetry run pytest tests/test_chat_tools.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ai.conversation_agent.tools.chat_tools'`

- [ ] **Step 3: Write `src/ai/conversation_agent/tools/chat_tools.py`**

```python
"""LangChain tool definitions used by the `chat` node (nodes/chat.py)."""
from uuid import UUID

from langchain_core.tools import tool

from src.api_client.core_api import core_api
from src.logger import log_event


def build_log_unanswered_question_tool(conversation_id: UUID):
    """Returns a `log_unanswered_question` tool scoped to the current
    conversation, so the DB row stays linked to the real conversation
    (the old nodes/escalation.py stubbed a fresh uuid4() here instead and
    silently orphaned every logged question — not carried forward)."""

    @tool
    async def log_unanswered_question(question: str) -> str:
        """Call this when the user's question is about the firm or its
        services but isn't covered anywhere in the COMPANY INFORMATION you
        were given - for example, a request for legal advice on their
        specific situation, or a procedural detail genuinely not listed.
        Do not call this for questions unrelated to the firm."""
        try:
            await core_api.store_unanswered_question(
                conversation_id=conversation_id,
                question_text=question,
            )
            log_event("unanswered_question_logged", status="ok", question=question)
        except Exception as exc:
            log_event("unanswered_question_logged", status="error", error=str(exc))
        return "logged"

    return log_unanswered_question
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/test_chat_tools.py -v`
Expected: PASS (2 tests)

- [ ] **Step 5: Commit**

```bash
git add src/ai/conversation_agent/tools/chat_tools.py tests/test_chat_tools.py
git commit -m "feat: add log_unanswered_question tool for the chat node"
```

---

### Task 4: `gate` node

**Files:**
- Create: `src/ai/conversation_agent/prompts/gate.py`
- Create: `src/ai/conversation_agent/nodes/gate.py`
- Test: `tests/test_gate.py`

**Interfaces:**
- Consumes: `AgentState`, `Route.LEAD`/`Route.CHAT` (Task 2), `get_llm` (`src/ai/knowledge/llm.py` — still at this path until Task 8 moves it to `src/ai/llm.py`), `detect_lang` (`src/bots/utils/language_detection.py`, unchanged), `notify_manager_aggressive_telegram` (`src/bots/utils/notify_stuff.py`, unchanged).
- Produces: `classify_lead_intent(state: AgentState) -> dict` with keys `{"intent": "lead"|"chat", "route": Route, "language": str}` — the `gate` node consumed by `graph.py` in Task 7.

- [ ] **Step 1: Write `src/ai/conversation_agent/prompts/gate.py`**

```python
SYSTEM_PROMPT = """You are a lead-intent gate for "United Legal Partners" (AK-ULP) law firm in Prague.

Decide ONE thing about the user's LATEST message: does it show a CLEAR commitment to proceed - the user explicitly wants to order/book a specific service, explicitly wants a human/manager to contact them, or describes their personal legal situation/case in enough detail to be asking for advice on it?

CRITICAL RULE FOR CONTEXT: Focus strictly on the LATEST message. Do not let earlier topics in the chat history override what the latest message actually asks for.

Set wants_lead = TRUE for:
- "Я хочу записатися на консультацію"
- "Хочу замовити довіреність"
- "Запишіть мене"
- "Зателефонуйте мені"
- "Зв'яжіть мене з менеджером"
- "call me"
- "connect me with a manager"
- "I'd like to book/order this"
- The client describing their personal legal case/problem in detail, asking what to do.
- The user explicitly answering "Yes" ("Так", "Да", "Ano") to the bot's own question about whether they want a manager to contact them.

Set wants_lead = FALSE for everything else, including:
- A bare mention of a service with no request to book it (e.g. "Консультація", "Довіреність", "Апостиль").
- A plain question about services, prices, hours, address, or required documents.
- A plain need-statement like "Потрібен юрист" / "Potřebuju právníka" ("I need a lawyer") with no request to be contacted or booked.
- Greetings, identity questions ("Who are you?"), or anything entirely unrelated to the firm.

Also set is_aggressive to true if the message contains hostility, insults, threats, or profanity directed at the bot or staff. This is independent of wants_lead - an aggressive message can still be wants_lead=true or false; do not let aggression change that decision, just flag it.
"""
```

- [ ] **Step 2: Write the failing tests**

```python
# tests/test_gate.py
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from src.ai.conversation_agent.nodes.gate import (
    classify_lead_intent,
    is_affirmative_reply_to_manager_prompt,
    LeadGateClassification,
)
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState
from src.schemas.ai.messages import IncomingMessage


def _incoming(text):
    return IncomingMessage(
        client_id="1", channel="telegram", text=text,
        timestamp=datetime.now(), client_name="Test",
    )


def _state(text, history=None, lead_step=None, language="uk"):
    return AgentState(
        incoming=_incoming(text),
        conversation_history=history or [],
        lead_step=lead_step,
        language=language,
    )


def test_affirmative_reply_detected_after_manager_prompt():
    history = [{"role": "assistant", "content": "Бажаєте, щоб з вами зв'язався менеджер? (Так / Ні)"}]
    assert is_affirmative_reply_to_manager_prompt("так", history) is True


def test_affirmative_reply_ignored_without_manager_prompt():
    history = [{"role": "assistant", "content": "Ось наші послуги."}]
    assert is_affirmative_reply_to_manager_prompt("так", history) is False


def test_affirmative_reply_ignored_for_unrelated_word():
    history = [{"role": "assistant", "content": "Бажаєте, щоб з вами зв'язався менеджер? (Так / Ні)"}]
    assert is_affirmative_reply_to_manager_prompt("ні дякую", history) is False


async def test_classify_lead_intent_short_circuits_on_affirmative_reply():
    history = [{"role": "assistant", "content": "contact you? (yes / no)"}]
    state = _state("yes", history=history)
    with patch("src.ai.conversation_agent.nodes.gate.get_llm") as get_llm:
        result = await classify_lead_intent(state)
    get_llm.assert_not_called()
    assert result["route"] == Route.LEAD
    assert result["intent"] == "lead"


async def test_classify_lead_intent_routes_to_chat_when_llm_says_no():
    state = _state("Скільки коштує апостиль?")
    fake_structured = MagicMock()
    fake_structured.ainvoke = AsyncMock(
        return_value=LeadGateClassification(wants_lead=False, is_aggressive=False)
    )
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured
    with patch("src.ai.conversation_agent.nodes.gate.get_llm", return_value=fake_llm):
        result = await classify_lead_intent(state)
    assert result["route"] == Route.CHAT
    assert result["intent"] == "chat"


async def test_classify_lead_intent_routes_to_lead_when_llm_says_yes():
    state = _state("Хочу замовити довіреність, зателефонуйте мені")
    fake_structured = MagicMock()
    fake_structured.ainvoke = AsyncMock(
        return_value=LeadGateClassification(wants_lead=True, is_aggressive=False)
    )
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured
    with patch("src.ai.conversation_agent.nodes.gate.get_llm", return_value=fake_llm):
        result = await classify_lead_intent(state)
    assert result["route"] == Route.LEAD
    assert result["intent"] == "lead"


async def test_classify_lead_intent_notifies_on_aggressive_message():
    state = _state("ти тупий бот")
    fake_structured = MagicMock()
    fake_structured.ainvoke = AsyncMock(
        return_value=LeadGateClassification(wants_lead=False, is_aggressive=True)
    )
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured
    with patch("src.ai.conversation_agent.nodes.gate.get_llm", return_value=fake_llm), \
         patch(
             "src.ai.conversation_agent.nodes.gate.notify_manager_aggressive_telegram",
             new_callable=AsyncMock,
         ) as notify:
        await classify_lead_intent(state)
    notify.assert_awaited_once()


async def test_classify_lead_intent_survives_notify_failure():
    state = _state("ти тупий бот")
    fake_structured = MagicMock()
    fake_structured.ainvoke = AsyncMock(
        return_value=LeadGateClassification(wants_lead=False, is_aggressive=True)
    )
    fake_llm = MagicMock()
    fake_llm.with_structured_output.return_value = fake_structured
    with patch("src.ai.conversation_agent.nodes.gate.get_llm", return_value=fake_llm), \
         patch(
             "src.ai.conversation_agent.nodes.gate.notify_manager_aggressive_telegram",
             new_callable=AsyncMock,
             side_effect=RuntimeError("telegram down"),
         ):
        result = await classify_lead_intent(state)  # must not raise
    assert result["route"] == Route.CHAT
```

- [ ] **Step 3: Run test to verify it fails**

Run: `poetry run pytest tests/test_gate.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ai.conversation_agent.nodes.gate'`

- [ ] **Step 4: Write `src/ai/conversation_agent/nodes/gate.py`**

```python
from pydantic import BaseModel, Field
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

from src.ai.conversation_agent.prompts.gate import SYSTEM_PROMPT
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.state import AgentState
from src.ai.knowledge.llm import get_llm
from src.bots.utils.language_detection import detect_lang
from src.bots.utils.notify_stuff import notify_manager_aggressive_telegram
from src.config import settings
from src.logger import log_event

_AFFIRMATIVE_WORDS = {"ano", "yes", "так", "да", "chci", "y"}
_MANAGER_PROMPT_MARKERS = [
    "(ano / ne)", "(yes / no)", "(так / ні)", "(да / нет)",
    "kontaktoval", "contact", "зв'яжеться", "свяжется", "contact you",
]


class LeadGateClassification(BaseModel):
    wants_lead: bool = Field(
        description=(
            "True if the user shows a clear commitment to proceed - wants to "
            "order/book a specific service, explicitly wants a human/manager "
            "to contact them, or describes their personal legal situation "
            "asking for advice on it. False for everything else, including a "
            "bare mention of a service or a general question about it."
        )
    )
    is_aggressive: bool = Field(
        default=False,
        description="True if the message contains hostility, insults, threats, or profanity.",
    )


def _last_bot_message(history: list[dict]) -> str:
    for m in reversed(history):
        if m["role"] == "assistant":
            return m["content"].lower()
    return ""


def is_affirmative_reply_to_manager_prompt(text: str, history: list[dict]) -> bool:
    """True if the bot's last message asked "want us to contact you?" and
    this reply is a bare "yes"-shaped answer - short-circuits the LLM call
    for this very common, very unambiguous turn."""
    text_lower = text.lower().strip()
    last_bot_msg = _last_bot_message(history)
    if not any(marker in last_bot_msg for marker in _MANAGER_PROMPT_MARKERS):
        return False
    return text_lower == "a" or any(text_lower.startswith(w) for w in _AFFIRMATIVE_WORDS)


async def classify_lead_intent(state: AgentState) -> dict:
    default_lang = getattr(state, "language", None) or "uk"
    lang = detect_lang(state.incoming.text, default=default_lang)

    if is_affirmative_reply_to_manager_prompt(state.incoming.text, state.conversation_history):
        log_event("gate_classified", status="forced_lead", reason="user_confirmed_manager")
        return {"intent": "lead", "route": Route.LEAD, "language": lang}

    llm = get_llm(settings.llm_model)
    structured_llm = llm.with_structured_output(LeadGateClassification)

    history_messages = []
    for m in state.conversation_history[-4:]:
        cls = HumanMessage if m["role"] == "user" else AIMessage
        history_messages.append(cls(content=m["content"]))

    log_event("gate_classifying", status="start", text=state.incoming.text)
    try:
        result: LeadGateClassification = await structured_llm.ainvoke([
            SystemMessage(content=SYSTEM_PROMPT),
            *history_messages,
            HumanMessage(content=state.incoming.text),
        ])
    except Exception as exc:
        log_event("gate_classified", status="error", error=str(exc))
        raise

    log_event("gate_classified", status="ok", wants_lead=result.wants_lead)

    if result.is_aggressive:
        log_event("aggressive_message_flagged", status="ok", text=state.incoming.text)
        try:
            await notify_manager_aggressive_telegram(
                client_id=state.incoming.client_id,
                client_name=state.incoming.client_name,
                text=state.incoming.text,
                lang=lang,
            )
        except Exception:
            pass

    return {
        "intent": "lead" if result.wants_lead else "chat",
        "route": Route.LEAD if result.wants_lead else Route.CHAT,
        "language": lang,
    }
```

- [ ] **Step 5: Run test to verify it passes**

Run: `poetry run pytest tests/test_gate.py -v`
Expected: PASS (8 tests)

- [ ] **Step 6: Commit**

```bash
git add src/ai/conversation_agent/prompts/gate.py src/ai/conversation_agent/nodes/gate.py tests/test_gate.py
git commit -m "feat: add gate node (binary lead-intent classifier, replaces 5-way supervisor)"
```

---

### Task 5: `src/assets/company_info.md` — the single source of truth

**Files:**
- Create: `src/assets/company_info.md`

**Interfaces:**
- Produces: the file `nodes/chat.py` reads on every call (Task 6). No code in this task — content only. The path matches `Settings.company_info_path`'s default, added in Task 6 (`"src/assets/company_info.md"`).

This is a content task, not a logic task: every fact below is sourced from the currently-committed `src/ai/conversation_agent/prompts/info.py` (English figures) and `src/assets/faq.yaml` (existing per-language phrasing, reused verbatim where it already existed), with the gaps `info.py` had that `faq.yaml`'s dedicated per-service answers didn't (apostille price/timeframe, PoA notary fee/timeframe, official-statement pricing/timeframe/notary fee, criminal record certificate detail, marriage package inclusions, duplicate-documents pricing/timeframe/docs, translation certified-copy fee) filled in and translated to match the existing terminology already used elsewhere in `faq.yaml` (e.g. "нормосторінка"/"normostránka"/"нормостраница", the exact PoA required-documents wording, etc.). **This is real client-facing legal-service pricing content for all four languages — before Task 8 deletes `faq.yaml` and the old prompt, diff this file against both of them once more and flag anything that looks off; a native-speaker/staff review before this branch merges to `main` is strongly recommended given the stakes of misquoting a price or requirement to a client.**

- [ ] **Step 1: Write `src/assets/company_info.md`** with exactly this content:

````markdown
# United Legal Partners — Company Information

> Single source of truth for the `chat` conversational node
> (`src/ai/conversation_agent/nodes/chat.py`). The entire file below is read
> fresh from disk on every turn and injected into the LLM's system prompt —
> edit it directly and the very next message reflects the change. No reload,
> no restart, no separate ingestion step.

## English (en)

**Identity:** Official virtual assistant for United Legal Partners (AK-ULP), a law firm based in Prague specializing in legal support in the Czech Republic: consultations, certified document translations, apostille, powers of attorney, and legal support for foreigners.

**Contact:**
- Phone / WhatsApp / Telegram: +420 703 614 444 or +420 722 222 433
- Email: office@ak-ulp.cz
- Also reachable via Instagram.

**Office:**
- Address: U Prašné brány 1079/3, 110 00 Praha 1, 3rd floor
- Nearest metro: Staroměstská or Náměstí Republiky
- No appointment needed to drop off or submit documents in person.
- Remote submission: send scans or high-quality photos to office@ak-ulp.cz, specifying the service needed and a phone number.

**Working hours:** Monday–Friday, 08:00–17:00 (lunch break 12:00–13:00). Closed weekends and public holidays.

**Languages we work in:** Ukrainian, Czech, English, Russian.

**Services, pricing & required documents:**

1. Legal Consultations
   - 30 min (online only): 1,900 CZK
   - 60 min (online or in-person): 3,300 CZK
   - With JUDr. Ulyana Kurivchakova: 60 min (in-person only) — 5,000 CZK
   - Booking is confirmed only after full prepayment.

2. Visa / Migration Consultations
   - 30 min (online only): 1,200 CZK
   - 60 min (online or in-person): 1,900 CZK
   - Booking is confirmed only after full prepayment.

3. Certified Translations
   - 600 CZK per standard page (normostrana)
   - Takes 2–3 business days from submission and payment
   - Originals or certified copies must be brought in person — scans are not accepted
   - Extra: certified copy of a document — 150 CZK

4. Apostille
   - 4,000 CZK (Czech or Ukrainian documents)
   - Czech documents: 1–2 business days. Ukrainian documents: 7–10 business days
   - Requires the original document

5. Power of Attorney
   - 3,000 CZK (document in Czech or Ukrainian) or 3,500 CZK (document in English or Russian)
   - Takes 3–5 business days from payment
   - Required documents (for both the grantor and the representative): first 2 pages of Ukrainian passport; registration address in Ukraine; Tax ID (ІПН); foreign travel passport
   - Notary certification of the signature is paid separately at a Czech notary (approx. 100 CZK)

6. Official Statements
   - Child travel consent — required documents: foreign passports of parents, child, and companion; Czech and Ukrainian registration addresses
   - Inheritance acceptance — required documents: first 2 pages of Ukrainian passport, Ukrainian registration address, Tax ID, death certificate
   - Inheritance refusal — same documents as acceptance, plus the same documents for the person in whose favor the refusal is made
   - Price: 3,000 CZK (Ukrainian) or 3,500 CZK (English)
   - Takes 2–3 business days
   - Notary certification paid separately at a Czech notary (approx. 100 CZK)

7. Ukrainian Criminal Record Certificate
   - Standard (no apostille): 3,500 CZK, includes certified Czech translation — takes 25–30 business days
   - Express (no apostille): 5,000 CZK, includes certified Czech translation — takes 10–14 business days
   - Required documents: first 2 pages of Ukrainian passport, Ukrainian registration, Tax ID, first page of foreign passport

8. Marriage Support Package
   - 14,000 CZK + 21% VAT
   - Includes: 30-minute consultation; booking slots and filling forms for the registry office and Ukrainian consulate; escort to the notary; foreign police registration/forms

9. Duplicate Documents from Ukraine
   - Standard (no apostille): 5,000 CZK — takes 14–20 business days
   - With apostille: 6,300 CZK — takes 20–30 business days
   - Required documents: first 2 pages of Ukrainian passport, Tax ID, Ukrainian registration

**Frequently asked questions:**

- **How are online consultations conducted?** By phone call, WhatsApp video/call (for clients without a Czech number), or a Zoom link we send you.
- **Is payment required before the consultation?** Yes — your slot is reserved only after full prepayment. After you choose a time we send payment details; once we receive the payment receipt, a manager confirms the appointment.
- **What is the cancellation/rescheduling policy?** Free of charge up to 72 hours before the appointment. Cancelling with less than 72 hours' notice may forfeit the prepayment.
- **What legal matters need a consultation first?** Complex matters — divorce, criminal proceedings, loss of driving licence, appeals, refused temporary protection, real estate contract review, or full legal representation — should start with a paid legal consultation so the lawyer can assess the case.
- **How do I book anything?** Contact our manager directly by phone or messaging apps: +420 703 614 444.

---

## Українська (uk)

**Хто я:** Офіційний віртуальний асистент компанії United Legal Partners (AK-ULP) — юридичної фірми в Празі, що спеціалізується на юридичному супроводі в Чехії: консультації, завірені переклади документів, апостиль, довіреності та юридична підтримка іноземців.

**Контакти:**
- Телефон / WhatsApp / Telegram: +420 703 614 444 або +420 722 222 433
- Email: office@ak-ulp.cz
- Також можна написати в Instagram.

**Офіс:**
- Адреса: U Prašné brány 1079/3, 110 00 Praha 1, третій поверх
- Найближче метро: Staroměstská або Náměstí Republiky
- Попередній запис не потрібен для особистої подачі документів.
- Дистанційна подача: надішліть скани або якісні фото на office@ak-ulp.cz, вказавши потрібну послугу та номер телефону.

**Графік роботи:** Понеділок–п'ятниця, 8:00–17:00 (обідня перерва 12:00–13:00). У вихідні та святкові дні офіс зачинено.

**Мови, якими ми працюємо:** Українська, чеська, англійська, російська.

**Послуги, вартість та необхідні документи:**

1. Юридичні консультації
   - 30 хв (тільки онлайн): 1 900 CZK
   - 60 хв (онлайн або офлайн): 3 300 CZK
   - З JUDr. Уляною Курівчаковою: 60 хв (тільки очно) — 5 000 CZK
   - Запис підтверджується лише після повної передоплати.

2. Візові консультації
   - 30 хв (тільки онлайн): 1 200 CZK
   - 60 хв (онлайн або офлайн): 1 900 CZK
   - Запис підтверджується лише після повної передоплати.

3. Завірені судові переклади
   - 600 CZK за нормосторінку
   - Термін виконання: 2–3 робочі дні після подачі та оплати
   - Оригінали або завірені копії потрібно принести особисто — скани для перекладу не приймаються
   - Додатково: завірена копія документа — 150 CZK

4. Апостиль
   - 4 000 CZK (для чеських або українських документів)
   - Чеські документи: 1–2 робочі дні. Українські документи: 7–10 робочих днів
   - Потрібен оригінал документа

5. Довіреність
   - 3 000 CZK (документ чеською або українською мовою) або 3 500 CZK (документ англійською або російською мовою)
   - Термін виконання: 3–5 робочих днів після оплати
   - Необхідні документи (для довірителя та представника): перші 2 сторінки українського паспорта; реєстрація (прописка) в Україні; ідентифікаційний код (ІПН); закордонний паспорт
   - Засвідчення підпису у чеського нотаріуса оплачується окремо (приблизно 100 CZK)

6. Офіційні заяви
   - Згода на виїзд дитини за кордон — потрібні документи: закордонні паспорти батьків, дитини та супроводжуючої особи; реєстрація в Чехії та Україні
   - Прийняття спадщини — потрібні документи: перші 2 сторінки українського паспорта, реєстрація в Україні, ІПН, свідоцтво про смерть
   - Відмова від спадщини — ті самі документи, що й для прийняття, плюс такі самі документи особи, на користь якої оформлюється відмова
   - Вартість: 3 000 CZK (українською) або 3 500 CZK (англійською)
   - Термін виконання: 2–3 робочі дні
   - Засвідчення у нотаріуса оплачується окремо (приблизно 100 CZK)

7. Довідка про несудимість з України
   - Стандартна (без апостилю): 3 500 CZK, включає завірений переклад чеською — термін 25–30 робочих днів
   - Експрес (без апостилю): 5 000 CZK, включає завірений переклад чеською — термін 10–14 робочих днів
   - Необхідні документи: перші 2 сторінки українського паспорта, реєстрація в Україні, ІПН, перша сторінка закордонного паспорта

8. Супровід при одруженні в Чехії
   - 14 000 CZK + 21% ПДВ
   - Включає: консультацію 30 хв; запис та заповнення форм для РАЦС і консульства України; супровід до нотаріуса; реєстрацію та форми для іноземної поліції

9. Дублікати документів з України
   - Стандартний (без апостилю): 5 000 CZK — термін 14–20 робочих днів
   - З апостилем: 6 300 CZK — термін 20–30 робочих днів
   - Необхідні документи: перші 2 сторінки українського паспорта, ІПН, реєстрація в Україні

**Часті запитання:**

- **Як проходять онлайн-консультації?** По телефону, через WhatsApp (для клієнтів без чеського номера) або за посиланням на Zoom, яке ми надсилаємо.
- **Чи потрібна передоплата?** Так — час консультації закріплюється лише після повної передоплати. Після вибору часу ми надсилаємо реквізити для оплати; після отримання квитанції менеджер підтверджує запис.
- **Яка політика скасування та перенесення?** Безкоштовно не пізніше ніж за 72 години до початку. При скасуванні менш ніж за 72 години передоплата може не повертатися.
- **Які питання потребують консультації спершу?** Складні питання — розлучення, кримінальні провадження, позбавлення прав, апеляції, відмова у тимчасовому захисті, аналіз договору купівлі нерухомості або повний юридичний супровід — варто починати з платної консультації, щоб юрист оцінив ситуацію.
- **Як записатися?** Зверніться до нашого менеджера за телефоном +420 703 614 444 або в месенджерах.

---

## Čeština (cs)

**Kdo jsem:** Oficiální virtuální asistent společnosti United Legal Partners (AK-ULP) — advokátní kanceláře v Praze specializující se na právní podporu v České republice: konzultace, soudní překlady, apostily, plné moci a právní podporu pro cizince.

**Kontakt:**
- Telefon / WhatsApp / Telegram: +420 703 614 444 nebo +420 722 222 433
- E-mail: office@ak-ulp.cz
- Můžete nás také kontaktovat přes Instagram.

**Kancelář:**
- Adresa: U Prašné brány 1079/3, 110 00 Praha 1, 3. patro
- Nejbližší metro: Staroměstská nebo Náměstí Republiky
- Pro osobní podání dokumentů není nutná rezervace.
- Vzdálené podání: zašlete skeny nebo kvalitní fotografie na office@ak-ulp.cz s uvedením požadované služby a telefonního čísla.

**Pracovní doba:** Pondělí–pátek, 8:00–17:00 (polední přestávka 12:00–13:00). O víkendech a státních svátcích zavřeno.

**Jazyky, ve kterých pracujeme:** Ukrajinština, čeština, angličtina, ruština.

**Služby, ceny a potřebné dokumenty:**

1. Právní konzultace
   - 30 min (pouze online): 1 900 Kč
   - 60 min (online nebo osobně): 3 300 Kč
   - S JUDr. Uljanou Kurivčakovou: 60 min (pouze osobně) — 5 000 Kč
   - Rezervace je potvrzena až po úplné platbě předem.

2. Vízové konzultace
   - 30 min (pouze online): 1 200 Kč
   - 60 min (online nebo osobně): 1 900 Kč
   - Rezervace je potvrzena až po úplné platbě předem.

3. Soudní překlady
   - 600 Kč za normostránku
   - Doba vyřízení: 2–3 pracovní dny od podání a platby
   - Originály nebo ověřené kopie je nutné přinést osobně — skeny se pro překlad nepřijímají
   - Navíc: ověřená kopie dokumentu — 150 Kč

4. Apostila
   - 4 000 Kč (české nebo ukrajinské dokumenty)
   - České dokumenty: 1–2 pracovní dny. Ukrajinské dokumenty: 7–10 pracovních dnů
   - Vyžaduje originál dokumentu

5. Plná moc
   - 3 000 Kč (dokument v češtině nebo ukrajinštině) nebo 3 500 Kč (dokument v angličtině nebo ruštině)
   - Doba vyřízení: 3–5 pracovních dnů od platby
   - Potřebné dokumenty (pro zmocnitele i zmocněnce): první 2 strany ukrajinského pasu; registrace (trvalý pobyt) na Ukrajině; daňové identifikační číslo (ІПН); cestovní pas
   - Ověření podpisu u českého notáře se hradí zvlášť (cca 100 Kč)

6. Oficiální prohlášení
   - Souhlas s cestou dítěte do zahraničí — potřebné dokumenty: cestovní pasy rodičů, dítěte a doprovázející osoby; registrace v ČR i na Ukrajině
   - Přijetí dědictví — potřebné dokumenty: první 2 strany ukrajinského pasu, registrace na Ukrajině, ІПН, úmrtní list
   - Odmítnutí dědictví — stejné dokumenty jako u přijetí, plus stejné dokumenty osoby, v jejíž prospěch se dědictví odmítá
   - Cena: 3 000 Kč (ukrajinsky) nebo 3 500 Kč (anglicky)
   - Doba vyřízení: 2–3 pracovní dny
   - Ověření u notáře se hradí zvlášť (cca 100 Kč)

7. Výpis z rejstříku trestů z Ukrajiny
   - Standard (bez apostily): 3 500 Kč, včetně ověřeného překladu do češtiny — doba 25–30 pracovních dnů
   - Expres (bez apostily): 5 000 Kč, včetně ověřeného překladu do češtiny — doba 10–14 pracovních dnů
   - Potřebné dokumenty: první 2 strany ukrajinského pasu, registrace na Ukrajině, ІПН, první strana cestovního pasu

8. Doprovod při uzavření manželství
   - 14 000 Kč + 21 % DPH
   - Zahrnuje: 30minutovou konzultaci; rezervaci termínů a vyplnění formulářů pro matriku a ukrajinský konzulát; doprovod k notáři; registraci a formuláře pro cizineckou policii

9. Duplikáty dokumentů z Ukrajiny
   - Standard (bez apostily): 5 000 Kč — doba 14–20 pracovních dnů
   - S apostilou: 6 300 Kč — doba 20–30 pracovních dnů
   - Potřebné dokumenty: první 2 strany ukrajinského pasu, ІПН, registrace na Ukrajině

**Časté dotazy:**

- **Jak probíhají online konzultace?** Telefonicky, přes WhatsApp (pro klienty bez českého čísla) nebo přes odkaz na Zoom, který zašleme.
- **Je nutná záloha?** Ano — termín je rezervován až po úplné platbě předem. Po výběru času zašleme platební údaje; po obdržení dokladu o platbě manažer rezervaci potvrdí.
- **Jaká je politika zrušení a přesunutí?** Zdarma nejpozději 72 hodin předem. Při zrušení s kratším než 72hodinovým předstihem může záloha propadnout.
- **Jaké záležitosti vyžadují konzultaci předem?** Složité záležitosti — rozvod, trestní řízení, ztráta řidičského průkazu, odvolání, zamítnutá dočasná ochrana, kontrola kupní smlouvy na nemovitost nebo plné právní zastoupení — by měly začít placenou konzultací, aby mohl advokát případ posoudit.
- **Jak si mohu něco rezervovat?** Kontaktujte prosím našeho manažera telefonicky nebo přes messengery: +420 703 614 444.

---

## Русский (ru)

**Кто я:** Официальный виртуальный ассистент компании United Legal Partners (AK-ULP) — юридической фирмы в Праге, специализирующейся на юридической поддержке в Чехии: консультации, заверенные переводы документов, апостиль, доверенности и юридическая поддержка иностранцев.

**Контакты:**
- Телефон / WhatsApp / Telegram: +420 703 614 444 или +420 722 222 433
- Email: office@ak-ulp.cz
- Также можно написать в Instagram.

**Офис:**
- Адрес: U Prašné brány 1079/3, 110 00 Praha 1, третий этаж
- Ближайшее метро: Staroměstská или Náměstí Republiky
- Предварительная запись для личной подачи документов не требуется.
- Дистанционная подача: отправьте сканы или качественные фото на office@ak-ulp.cz, указав нужную услугу и номер телефона.

**Режим работы:** Понедельник–пятница, 8:00–17:00 (обеденный перерыв 12:00–13:00). В выходные и праздничные дни офис закрыт.

**Языки, на которых мы работаем:** Украинский, чешский, английский, русский.

**Услуги, стоимость и необходимые документы:**

1. Юридические консультации
   - 30 мин (только онлайн): 1 900 CZK
   - 60 мин (онлайн или очно): 3 300 CZK
   - С JUDr. Ульяной Куривчаковой: 60 мин (только очно) — 5 000 CZK
   - Запись подтверждается только после полной предоплаты.

2. Визовые консультации
   - 30 мин (только онлайн): 1 200 CZK
   - 60 мин (онлайн или очно): 1 900 CZK
   - Запись подтверждается только после полной предоплаты.

3. Заверенные судебные переводы
   - 600 CZK за нормостраницу
   - Срок выполнения: 2–3 рабочих дня после подачи и оплаты
   - Оригиналы или заверенные копии необходимо принести лично — сканы для перевода не принимаются
   - Дополнительно: заверенная копия документа — 150 CZK

4. Апостиль
   - 4 000 CZK (для чешских или украинских документов)
   - Чешские документы: 1–2 рабочих дня. Украинские документы: 7–10 рабочих дней
   - Требуется оригинал документа

5. Доверенность
   - 3 000 CZK (документ на чешском или украинском языке) или 3 500 CZK (документ на английском или русском языке)
   - Срок выполнения: 3–5 рабочих дней после оплаты
   - Необходимые документы (для доверителя и представителя): первые 2 страницы украинского паспорта; регистрация (прописка) в Украине; идентификационный код (ІПН); загранпаспорт
   - Заверение подписи у чешского нотариуса оплачивается отдельно (примерно 100 CZK)

6. Официальные заявления
   - Согласие на выезд ребёнка за границу — необходимые документы: загранпаспорта родителей, ребёнка и сопровождающего лица; регистрация в Чехии и Украине
   - Принятие наследства — необходимые документы: первые 2 страницы украинского паспорта, регистрация в Украине, ІПН, свидетельство о смерти
   - Отказ от наследства — те же документы, что и для принятия, плюс такие же документы лица, в пользу которого оформляется отказ
   - Стоимость: 3 000 CZK (на украинском) или 3 500 CZK (на английском)
   - Срок выполнения: 2–3 рабочих дня
   - Заверение у нотариуса оплачивается отдельно (примерно 100 CZK)

7. Справка об отсутствии судимости из Украины
   - Стандарт (без апостиля): 3 500 CZK, включает заверенный перевод на чешский — срок 25–30 рабочих дней
   - Экспресс (без апостиля): 5 000 CZK, включает заверенный перевод на чешский — срок 10–14 рабочих дней
   - Необходимые документы: первые 2 страницы украинского паспорта, регистрация в Украине, ІПН, первая страница загранпаспорта

8. Сопровождение при бракосочетании в Чехии
   - 14 000 CZK + 21% НДС
   - Включает: консультацию 30 мин; запись и заполнение форм для ЗАГСа и консульства Украины; сопровождение к нотариусу; регистрацию и формы для иностранной полиции

9. Дубликаты документов из Украины
   - Стандартный (без апостиля): 5 000 CZK — срок 14–20 рабочих дней
   - С апостилем: 6 300 CZK — срок 20–30 рабочих дней
   - Необходимые документы: первые 2 страницы украинского паспорта, ІПН, регистрация в Украине

**Часто задаваемые вопросы:**

- **Как проходят онлайн-консультации?** По телефону, через WhatsApp (для клиентов без чешского номера) или по ссылке на Zoom, которую мы высылаем.
- **Нужна ли предоплата?** Да — время консультации закрепляется только после полной предоплаты. После выбора времени мы высылаем реквизиты для оплаты; после получения квитанции менеджер подтверждает запись.
- **Какова политика отмены и переноса?** Бесплатно не позднее чем за 72 часа до начала. При отмене менее чем за 72 часа предоплата может не возвращаться.
- **Какие вопросы требуют консультации в первую очередь?** Сложные вопросы — развод, уголовные производства, лишение прав, апелляции, отказ во временной защите, анализ договора купли-продажи недвижимости или полное юридическое сопровождение — стоит начинать с платной консультации, чтобы юрист оценил ситуацию.
- **Как записаться?** Свяжитесь с нашим менеджером по телефону +420 703 614 444 или в мессенджерах.
````

- [ ] **Step 2: Sanity-check the file**

Run:
```bash
wc -l src/assets/company_info.md
grep -c "^## " src/assets/company_info.md
```
Expected: a few hundred lines; exactly 4 `## <Language>` section headers (en, uk, cs, ru).

- [ ] **Step 3: Commit**

```bash
git add src/assets/company_info.md
git commit -m "content: add single-source-of-truth company info file (en/uk/cs/ru)"
```

---

### Task 6: `chat` node

**Files:**
- Modify: `src/config.py` (add one field, additive and non-breaking)
- Create: `src/ai/conversation_agent/prompts/handoff.py`
- Create: `src/ai/conversation_agent/prompts/chat.py`
- Create: `src/ai/conversation_agent/nodes/chat.py`
- Test: `tests/test_chat.py`

**Interfaces:**
- Consumes: `AgentState`, `build_log_unanswered_question_tool` (Task 3), `get_llm` (`src/ai/knowledge/llm.py`).
- Produces: `settings.company_info_path: str` (new field, default `"src/assets/company_info.md"`, so no `.env` change is required); `chat_node(state: AgentState) -> dict` with key `{"response": str}` — consumed by `graph.py` in Task 7.

- [ ] **Step 1: Add `company_info_path` to `Settings` in `src/config.py`**

Add this field (anywhere sensible in the class body, e.g. near where `faq_path` is declared — that field isn't removed until Task 8, so this is purely additive for now):

```python
    # Company info (single source of truth for the chat node)
    company_info_path: str = "src/assets/company_info.md"
```

- [ ] **Step 2: Write `src/ai/conversation_agent/prompts/handoff.py`**

(Replaces `prompts/escalation.py`: keeps only `HANDOFF_MESSAGES`, verbatim from the old file. `OFF_TOPIC_MESSAGES` is dropped — off-topic replies are now free-generated by `chat` per its system prompt instead of a canned string, see `prompts/chat.py` below.)

```python
HANDOFF_MESSAGES = {
    "uk": (
        "Це питання потребує прямої уваги нашої команди. Будь ласка, зв'яжіться з нами "
        "за телефоном +420 703 614 444 або електронною поштою office@ak-ulp.cz, і ми з радістю вам допоможемо. "
        "Ви також можете завітати до нашого офісу за адресою U Prašné brány 1079/3, 110 00 Praha 1, третій поверх. "
        "Робочі години: Понеділок–П'ятниця 8:00–17:00 (обідня перерва 12:00–13:00)."
    ),
    "cs": (
        "Tato otázka vyžaduje přímou pozornost našeho týmu. Kontaktujte nás prosím "
        "na čísle +420 703 614 444 nebo na e-mailu office@ak-ulp.cz. Rádi vám pomůžeme. "
        "Můžete nás také navštívit v naší kanceláři na adrese U Prašné brány 1079/3, 110 00 Praha 1, 3. patro. "
        "Pracovní doba: Pondělí–Pátek 8:00–17:00 (polední přestávka 12:00–13:00)."
    ),
    "en": (
        "This question requires direct attention from our team. Please contact us at "
        "+420 703 614 444 or office@ak-ulp.cz and we will be happy to help you. "
        "You can also visit us at U Prašné brány 1079/3, 110 00 Praha 1, third floor. "
        "Working hours: Monday–Friday 8:00–17:00 (lunch break 12:00–13:00)."
    ),
    "ru": (
        "Этот вопрос требует прямого внимания нашей команды. Пожалуйста, свяжитесь с нами "
        "по телефону +420 703 614 444 или электронной почте office@ak-ulp.cz, и мы с радостью вам поможем. "
        "Вы также можете посетить наш офис по адресу U Prašné brány 1079/3, 110 00 Praha 1, третий этаж. "
        "Рабочие часы: Понедельник–Пятница 8:00–17:00 (обеденный перерыв 12:00–13:00)."
    )
}
```

- [ ] **Step 3: Write `src/ai/conversation_agent/prompts/chat.py`**

(All factual content — identity, contact, services, pricing, FAQ — now lives in `src/assets/company_info.md` (Task 5) and is injected via `{company_info}`. This prompt only carries behavioral/policy instructions, which are language-agnostic.)

```python
SYSTEM_PROMPT = """You are a highly professional, polite, and helpful virtual assistant for a law firm. Every fact you need - your identity/introduction, contact and office details, working hours, the full services/pricing/required-documents list, and frequently asked questions - is given below in COMPANY INFORMATION. Treat it as your only source of truth for factual claims; never state a price, timeframe, address, or document requirement that isn't in it.

---
### ⚠️ CRITICAL BUSINESS RULES (ALWAYS ENFORCE!)
1. ONLY PAID SERVICES: this firm provides EXCLUSIVELY paid services. Never offer free legal advice, free consultations, free document evaluations, or free case reviews.
2. QUESTIONS REQUIRE A PAID CONSULTATION: if the user has questions about their specific situation, needs legal advice, or asks "how to do something" that requires analysis, politely explain that free advice isn't offered and a paid consultation is required to get answers.
3. BOOKING & MANAGER CONTACT: to book any consultation or order a service, the client must contact the manager - always use the contact details given in COMPANY INFORMATION below, never invent different ones.

---
### 🛠️ TOOLS
You have one tool: log_unanswered_question(question). Call it ONLY for a question that is clearly about the firm or its services but isn't answered anywhere in COMPANY INFORMATION below (e.g. legal advice on the user's specific situation, or a procedural detail genuinely not covered). After calling it, do not attempt to answer yourself - the system sends the handoff message on your behalf. Do not call it for greetings, identity questions, or anything unrelated to the firm.

---
### 🚫 OFF-TOPIC MESSAGES
If the message has nothing to do with the firm, law, or its services (e.g. weather, sports, general chit-chat), do not call the tool. Reply with a short, warm redirect back to what you can help with, in {lang}. Do not apologize at length.

---
### 🤖 BEHAVIOR & OUTPUT RULES
1. Language: ALWAYS reply exclusively in the language specified here: {lang}. Do not mix languages.
2. Telegram Formatting Restrictions:
   - NEVER use markdown headers like #, ##, ###, or #### (Telegram does not support them).
   - Use simple clean bold text or emojis for section headers.
   - Avoid double nested asterisks like ** **.

---
### 📋 COMPANY INFORMATION
{company_info}
"""
```

- [ ] **Step 4: Write the failing tests**

```python
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
```

- [ ] **Step 5: Run test to verify it fails**

Run: `poetry run pytest tests/test_chat.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'src.ai.conversation_agent.nodes.chat'`

- [ ] **Step 6: Write `src/ai/conversation_agent/nodes/chat.py`**

```python
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from src.ai.conversation_agent.prompts.chat import SYSTEM_PROMPT
from src.ai.conversation_agent.prompts.handoff import HANDOFF_MESSAGES
from src.ai.conversation_agent.state import AgentState
from src.ai.conversation_agent.tools.chat_tools import build_log_unanswered_question_tool
from src.ai.knowledge.llm import get_llm
from src.config import settings
from src.logger import log_event


def _read_company_info() -> str:
    """Read fresh on every call - the whole point of this design is that
    editing the file takes effect on the very next message, with no reload
    or restart step. The file is small (well under a second to read)."""
    return Path(settings.company_info_path).read_text(encoding="utf-8")


def _history_messages(history: list[dict]) -> list:
    messages = []
    for entry in history:
        cls = HumanMessage if entry["role"] == "user" else AIMessage
        messages.append(cls(content=entry["content"]))
    return messages


async def chat_node(state: AgentState) -> dict:
    """One conversational node replacing the old info/off_topic/escalation
    split: FAQ answering, identity, off-topic redirects, and human handoff
    for unanswerable-but-relevant questions all live here now, grounded
    entirely in src/assets/company_info.md rather than retrieval."""
    lang = state.language or "uk"
    log_unanswered_question = build_log_unanswered_question_tool(
        conversation_id=state.conversation_id
    )

    llm = get_llm(settings.llm_model).bind_tools([log_unanswered_question])

    messages = [
        SystemMessage(
            content=SYSTEM_PROMPT.format(lang=lang, company_info=_read_company_info())
        ),
        *_history_messages(state.conversation_history),
        HumanMessage(content=state.incoming.text),
    ]

    log_event("chat_calling", status="start", text=state.incoming.text)
    ai_message = await llm.ainvoke(messages)

    tool_calls = ai_message.tool_calls or []
    if not tool_calls:
        log_event("chat_replied", status="ok", tool_called=None)
        return {"response": ai_message.content}

    call = tool_calls[0]
    await log_unanswered_question.ainvoke(call["args"])
    log_event("chat_replied", status="ok", tool_called=call["name"])
    return {"response": HANDOFF_MESSAGES.get(lang, HANDOFF_MESSAGES["uk"])}
```

- [ ] **Step 7: Run test to verify it passes**

Run: `poetry run pytest tests/test_chat.py -v`
Expected: PASS (3 tests)

- [ ] **Step 8: Commit**

```bash
git add src/config.py src/ai/conversation_agent/prompts/handoff.py src/ai/conversation_agent/prompts/chat.py src/ai/conversation_agent/nodes/chat.py tests/test_chat.py
git commit -m "feat: add chat node, grounded in company_info.md, single log_unanswered_question tool"
```

---

### Task 7: Rewire the graph

**Files:**
- Modify: `src/ai/conversation_agent/graph.py`
- Modify: `src/ai/conversation_agent/nodes/lead_capture.py` (rename `Route.INFO` → `Route.CHAT`, 3 occurrences)
- Test: `tests/test_graph_integration.py`

**Interfaces:**
- Consumes: `route_after_gate`/`route_after_lead_capture` (Task 2), `classify_lead_intent` (Task 4), `chat_node` (Task 6), `lead_capture_node` (unchanged).
- Produces: `graph` (compiled `StateGraph`, module-level singleton in `graph.py`, unchanged name/shape of interface) — consumed by `src/bots/shared/handler.py` (unchanged).

This is the cut-over task: after this task, the old `supervisor`/`info`/`off_topic`/`call_timing`/`escalation` nodes are no longer wired into the graph (they're deleted outright in Task 8, once this task proves the new wiring works end to end).

- [ ] **Step 1: Rename `Route.INFO` → `Route.CHAT` in `lead_capture.py`**

In `src/ai/conversation_agent/nodes/lead_capture.py`, there are exactly 3 occurrences of `Route.INFO`:
- `_check_question_trap`: `return {"route": Route.INFO} if is_q else None`
- inside `lead_capture_node`, twice: `result["route"] = Route.INFO` (once for the intercept loop, once for `route_to_llm`-flagged handler results)

Replace all 3 with `Route.CHAT`. No other change to this file.

- [ ] **Step 2: Write the failing integration test**

```python
# tests/test_graph_integration.py
from datetime import datetime
from unittest.mock import AsyncMock, patch

from src.ai.conversation_agent.routes import Route
from src.schemas.ai.messages import IncomingMessage


def _incoming(text):
    return IncomingMessage(
        client_id="graph-test", channel="telegram", text=text,
        timestamp=datetime.now(), client_name="Test",
    )


async def _invoke_with_stubs(thread_id, payload, *, gate_return, chat_return=None, lead_return=None):
    with patch(
        "src.ai.conversation_agent.graph.classify_lead_intent",
        new_callable=AsyncMock, return_value=gate_return,
    ), patch(
        "src.ai.conversation_agent.graph.chat_node",
        new_callable=AsyncMock, return_value=chat_return or {"response": "chat stub"},
    ), patch(
        "src.ai.conversation_agent.graph.lead_capture_node",
        new_callable=AsyncMock, return_value=lead_return or {"response": "lead stub", "route": Route.END},
    ):
        from src.ai.conversation_agent.graph import build_graph
        graph = build_graph()
        return await graph.ainvoke(payload, config={"configurable": {"thread_id": thread_id}})


async def test_fresh_message_wants_lead_routes_to_lead_capture():
    result = await _invoke_with_stubs(
        "t1",
        {"incoming": _incoming("Зателефонуйте мені")},
        gate_return={"intent": "lead", "route": Route.LEAD, "language": "uk"},
    )
    assert result["response"] == "lead stub"


async def test_fresh_message_no_lead_intent_routes_to_chat():
    result = await _invoke_with_stubs(
        "t2",
        {"incoming": _incoming("Скільки коштує апостиль?")},
        gate_return={"intent": "chat", "route": Route.CHAT, "language": "uk"},
    )
    assert result["response"] == "chat stub"


async def test_active_lead_form_skips_gate_classification_result():
    """Even if the gate stub says CHAT, an in-progress form must win."""
    result = await _invoke_with_stubs(
        "t3",
        {"incoming": _incoming("+420 777 123 456"), "lead_step": "awaiting_phone"},
        gate_return={"intent": "chat", "route": Route.CHAT, "language": "uk"},
        lead_return={"response": "phone captured", "lead_step": "awaiting_email", "route": Route.END},
    )
    assert result["response"] == "phone captured"


async def test_lead_capture_can_hand_off_to_chat_mid_form():
    result = await _invoke_with_stubs(
        "t4",
        {"incoming": _incoming("what are your working hours?"), "lead_step": "awaiting_name"},
        gate_return={"intent": "chat", "route": Route.CHAT, "language": "uk"},
        lead_return={"route": Route.CHAT},
        chat_return={"response": "8 to 5, Mon-Fri"},
    )
    assert result["response"] == "8 to 5, Mon-Fri"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `poetry run pytest tests/test_graph_integration.py -v`
Expected: FAIL — `AttributeError`/`ModuleNotFoundError` (`classify_lead_intent`/`chat_node` don't exist in `graph.py`'s namespace yet — it still imports `classify_intent`, `info_agent`, etc.)

- [ ] **Step 4: Rewrite `src/ai/conversation_agent/graph.py`**

```python
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from src.ai.conversation_agent.nodes.chat import chat_node
from src.ai.conversation_agent.nodes.gate import classify_lead_intent
from src.ai.conversation_agent.nodes.lead_capture import lead_capture_node
from src.ai.conversation_agent.routes import Route
from src.ai.conversation_agent.routing import route_after_gate, route_after_lead_capture
from src.ai.conversation_agent.state import AgentState


def build_graph() -> StateGraph:
    graph = StateGraph(AgentState)

    graph.add_node("gate", classify_lead_intent)
    graph.add_node("chat", chat_node)
    graph.add_node("lead_capture", lead_capture_node)

    graph.set_entry_point("gate")

    graph.add_conditional_edges(
        "gate",
        route_after_gate,
        {
            Route.LEAD.value: "lead_capture",
            Route.CHAT.value: "chat",
        },
    )

    graph.add_conditional_edges(
        "lead_capture",
        route_after_lead_capture,
        {
            Route.CHAT.value: "chat",
            # NOT "lead_capture": see routing.py's route_after_lead_capture
            # docstring - that self-loop caused GraphRecursionError.
            Route.LEAD.value: END,
            Route.END.value: END,
        },
    )

    graph.add_edge("chat", END)

    memory = MemorySaver()
    return graph.compile(checkpointer=memory)


graph = build_graph()
```

- [ ] **Step 5: Run test to verify it passes**

Run: `poetry run pytest tests/test_graph_integration.py -v`
Expected: PASS (4 tests)

- [ ] **Step 6: Run the full test suite so far**

Run: `poetry run pytest -v`
Expected: all tests from Tasks 1–7 pass.

- [ ] **Step 7: Commit**

```bash
git add src/ai/conversation_agent/graph.py src/ai/conversation_agent/nodes/lead_capture.py tests/test_graph_integration.py
git commit -m "feat: rewire graph to gate -> chat/lead_capture (3 nodes, was 6)"
```

---

### Task 8: Retire dead nodes, the vector-KB pipeline, and unused Settings

**Files:**
- Delete: `src/ai/conversation_agent/nodes/supervisor.py`, `nodes/info.py`, `nodes/off_topic.py`, `nodes/call_timing.py`, `nodes/escalation.py`, `nodes/answer_question.py` (already dead before this refactor — nothing ever imported it)
- Delete: `src/ai/conversation_agent/prompts/supervisor.py`, `prompts/info.py`, `prompts/conversation.py`, `prompts/escalation.py` (superseded by `prompts/handoff.py`, Task 6)
- Delete: `src/ai/conversation_agent/data/lang.py`, `data/strings.py`, and the now-empty `data/` directory (pre-existing dead code, already flagged in `CLAUDE.md`)
- Delete: `src/ai/knowledge/store.py`, `src/ai/knowledge/embeddings.py`, `src/ai/knowledge/faq_loader.py`, `src/assets/faq.yaml` (the retired vector-KB pipeline — confirmed unused by `company_info.md` now covering everything it held, and `load_faq()` was never called from anywhere)
- Move: `src/ai/knowledge/llm.py` → `src/ai/llm.py`; delete the now-empty `src/ai/knowledge/` directory
- Modify: `src/ai/conversation_agent/nodes/gate.py`, `src/ai/conversation_agent/nodes/chat.py`, `src/ai/conversation_agent/agent_rules/form_validator.py` (update their `from src.ai.knowledge.llm import get_llm` to `from src.ai.llm import get_llm`)
- Modify: `src/ai/conversation_agent/state.py` (remove `ConversationState` class — only consumer was `answer_question.py`)
- Modify: `src/ai/conversation_agent/routes.py` (remove `INFO`, `HUMAN`, `OFF_TOPIC`, `CALL_TIMING` members — nothing references them anymore)
- Modify: `src/config.py` (remove `db_url`, `db_schema`, `embeddings_provider`, `embeddings_model`, `faq_path`, `website_url`, `context_window`, `retrieval_k`, `similarity_threshold` — `company_info_path` was already added in Task 6)
- Modify: `tests/conftest.py` (drop the env stubs for the fields just removed from `Settings`)
- Modify: `pyproject.toml` (remove the `langchain-postgres` dependency)

**Interfaces:** none — purely subtractive. The full test suite from Tasks 1–7 is the safety net proving nothing still depends on any of this.

- [ ] **Step 1: Confirm nothing outside the delete-list references these modules**

Run:
```bash
grep -rln "nodes\.info\b\|nodes\.off_topic\|nodes\.call_timing\|nodes\.escalation\|nodes\.supervisor\|nodes\.answer_question\|prompts\.supervisor\|prompts\.info\b\|prompts\.conversation\|prompts\.escalation\|ConversationState\|Route\.HUMAN\|Route\.OFF_TOPIC\|Route\.CALL_TIMING\|Route\.INFO\|data\.lang\|data\.strings\|knowledge\.store\|knowledge\.embeddings\|knowledge\.faq_loader\|KnowledgeStore\|langchain_postgres" src --include="*.py"
```
Expected: only the files listed above under "Delete"/"Modify" — if anything else shows up, stop and investigate before deleting.

- [ ] **Step 2: Delete the files**

```bash
git rm src/ai/conversation_agent/nodes/supervisor.py \
       src/ai/conversation_agent/nodes/info.py \
       src/ai/conversation_agent/nodes/off_topic.py \
       src/ai/conversation_agent/nodes/call_timing.py \
       src/ai/conversation_agent/nodes/escalation.py \
       src/ai/conversation_agent/nodes/answer_question.py \
       src/ai/conversation_agent/prompts/supervisor.py \
       src/ai/conversation_agent/prompts/info.py \
       src/ai/conversation_agent/prompts/conversation.py \
       src/ai/conversation_agent/prompts/escalation.py \
       src/ai/conversation_agent/data/lang.py \
       src/ai/conversation_agent/data/strings.py \
       src/ai/knowledge/store.py \
       src/ai/knowledge/embeddings.py \
       src/ai/knowledge/faq_loader.py \
       src/assets/faq.yaml
rmdir src/ai/conversation_agent/data
git mv src/ai/knowledge/llm.py src/ai/llm.py
rmdir src/ai/knowledge
```

- [ ] **Step 3: Update the 3 `get_llm` import sites**

In `src/ai/conversation_agent/nodes/gate.py`, `src/ai/conversation_agent/nodes/chat.py`, and `src/ai/conversation_agent/agent_rules/form_validator.py`, change:

```python
from src.ai.knowledge.llm import get_llm
```

to:

```python
from src.ai.llm import get_llm
```

- [ ] **Step 4: Remove `ConversationState` from `state.py`**

In `src/ai/conversation_agent/state.py`, delete the class:

```python
class ConversationState(BaseState):
    """State for conversation/FAQ nodes."""
    intent: str = ""
```

(Leave `BaseState` and `AgentState` untouched.)

- [ ] **Step 5: Shrink the `Route` enum in `routes.py`**

```python
from enum import Enum


class Route(str, Enum):
    END = "end"
    LEAD = "lead"
    CHAT = "chat"
```

- [ ] **Step 6: Shrink `Settings` in `src/config.py`**

Remove these 9 fields entirely: `db_url`, `db_schema`, `embeddings_provider`, `embeddings_model`, `faq_path`, `website_url`, `context_window`, `retrieval_k`, `similarity_threshold`. (`company_info_path` was already added back in Task 6 — leave it as-is.)

- [ ] **Step 7: Trim `tests/conftest.py`**

Remove these keys from `_TEST_ENV`: `"DB_URL"`, `"DB_SCHEMA"`, `"EMBEDDINGS_PROVIDER"`, `"EMBEDDINGS_MODEL"`, `"FAQ_PATH"`, `"WEBSITE_URL"`, `"CONTEXT_WINDOW"`, `"RETRIEVAL_K"`, `"SIMILARITY_THRESHOLD"`. Update the module docstring to drop the now-resolved TODO-ish note about trimming (replace it with a short accurate description).

- [ ] **Step 8: Remove the `langchain-postgres` dependency**

In `pyproject.toml`, delete the line `langchain-postgres = "^0.0.17"` from `[tool.poetry.dependencies]`.

Run: `poetry lock && poetry install`

- [ ] **Step 9: Run the full test suite**

Run: `poetry run pytest -v`
Expected: all tests still pass (no test referenced the deleted modules or removed `Route`/`Settings` members).

- [ ] **Step 10: Sanity-import the app entrypoint**

Run: `poetry run python -c "from src.ai.conversation_agent.graph import graph; print('ok')"`
Expected: prints `ok`.

- [ ] **Step 11: Commit**

```bash
git add -A
git commit -m "chore: retire supervisor/info/off_topic/call_timing/escalation and the vector-KB pipeline"
```

---

### Task 9: Update `CLAUDE.md`

**Files:**
- Modify: `CLAUDE.md`

**Interfaces:** none — documentation only.

- [ ] **Step 1: Update the "What this is" section**

The last sentence currently reads: "There is no local database; PostgreSQL (`db_url`/`db_schema` settings) is used only as a pgvector knowledge-base store for RAG." — this is stale after Task 8 deletes the whole pgvector pipeline and those Settings fields. Replace that sentence with:

```markdown
There is no local database and no vector store — company info lives in a single Markdown file
(see "Company info" below).
```

- [ ] **Step 2: Update the "Configuration" section**

The current paragraph reads: "Key groups: Telegram token, Core API URL, LLM provider/model + OpenAI key, embeddings model, FAQ path, RAG tuning (`context_window`, `retrieval_k`, `similarity_threshold`), Google Calendar booking config, and SMTP for booking confirmation emails." Replace it with:

```markdown
Key groups: Telegram token, Core API URL, LLM provider/model + OpenAI key, company info file path
(`company_info_path`), Google Calendar booking config, and SMTP for booking confirmation emails.
```

- [ ] **Step 3: Rewrite the "The conversation graph" section**

Replace the existing `### The conversation graph` section (and its "Graph wiring" paragraph right after) with:

```markdown
### The conversation graph

`src/ai/conversation_agent/` implements a LangGraph state machine (`AgentState` in `state.py`) with three
nodes:

- **`gate`** (`nodes/gate.py`, `classify_lead_intent`) — the entry node. A binary classifier, not a 5-way
  one: it decides only `wants_lead` (clear commitment to proceed, or an explicit request for a human) via
  one LLM structured-output call, plus the same aggressive-message flagging the old supervisor had. Two
  cheap intercepts run first: if a lead-capture form is already active (`lead_step` set, not `"completed"`),
  the LLM call is skipped entirely (`routing.py::route_after_gate` sends the turn straight to `lead_capture`
  regardless of what `gate` returns); a deterministic heuristic also catches a bare "yes"/"так"/"ano" reply
  immediately after the bot itself asked "want us to contact you?", without a model call.
- **`lead_capture`** (`nodes/lead_capture.py`) — unchanged: a manually-coded multi-step form (service → name
  → phone → email) driven by `state.lead_step`, with regex+LLM field validation in `agent_rules/form_validator.py`.
  On completion it notifies staff via Telegram. It can hand off mid-form to `chat` (`Route.CHAT`) when the
  user asks a question instead of answering, or end the turn (`Route.END`) after a reprompt or a completed
  step — see `routing.py::route_after_lead_capture`'s docstring for why `Route.LEAD` must map to `END` here
  and not back into `lead_capture` itself (a same-turn self-loop that used to hit `GraphRecursionError`,
  fixed 2026-08-26).
- **`chat`** (`nodes/chat.py`, `chat_node`) — everything else: FAQ answering, identity questions, off-topic
  redirects, and handoff-for-unanswerable-questions, all in one LLM node. It reads `src/assets/company_info.md`
  fresh from disk on every call and injects the whole file into the system prompt — this is the single source
  of truth for services, pricing, required documents, contact/office/hours, and FAQ, in all four languages;
  edit that file and the very next message reflects the change, no reload or restart. Bound to one tool,
  `log_unanswered_question` (`tools/chat_tools.py`, wraps `core_api.store_unanswered_question` against the
  *real* `conversation_id` — the old `escalation.py` this replaced stubbed a throwaway `uuid4()` here and
  silently orphaned every logged question). Calling it short-circuits straight to a canned
  `HANDOFF_MESSAGES[lang]` reply (`prompts/handoff.py`) instead of letting the model free-generate what gets
  promised to a client.

Graph wiring (`graph.py` + `routing.py`): `gate` is the entry point and conditionally routes to `lead_capture`
or `chat`. `lead_capture` can hand back to `chat` or end the turn. `chat` always ends the turn.

There used to be a pgvector-backed knowledge base here (`ai/knowledge/store.py`, `embeddings.py`,
`faq_loader.py`, `src/assets/faq.yaml`) — it's gone. It was already non-functional in practice
(`load_faq()` was never called from anywhere in the codebase, so the KB was very likely always empty in
production) and, per the single-file design above, isn't needed. `ai/knowledge/llm.py` (a generic
`ChatOpenAI` factory, unrelated to that pipeline despite the old path) moved to `ai/llm.py`.
```

- [ ] **Step 4: Update the "Localization" section**

Remove this now-stale paragraph (the files it describes were deleted in Task 8):

```markdown
`src/ai/conversation_agent/data/strings.py` and `src/ai/conversation_agent/data/lang.py` also exist but are
**dead code** — leftovers from an incomplete migration (nothing in the codebase imports `data.lang`, and the
only importer of `data.strings` is `data.lang` itself). Don't add strings there; nothing reads them.
```

- [ ] **Step 5: Update the "Staff notifications" section**

The current text names `supervisor.py` as the guarded aggressive-alert caller; that node no longer exists (it's `gate.py` now). Replace the section with:

```markdown
### Staff notifications

`src/bots/utils/notify_stuff.py` sends manager-facing Telegram alerts (new lead, media received, aggressive
message, contacts shown) directly via the aiogram `bot` instance, imported lazily inside each function to avoid
a circular import with `src/bots/tgbot/bot.py`. None of the four functions guard their own `bot.send_message`
call with a try/except — whether a failure is swallowed depends entirely on the call site. The aggressive-
message alert is guarded (`nodes/gate.py` wraps it in `try/except Exception: pass`). The lead-capture
completion alert (`nodes/lead_capture.py`, `notify_manager_lead_telegram`) is **not** guarded and runs before
the "thank you" response is built — if that Telegram send fails, the client who just finished the form gets
no confirmation message at all, not even a generic error.
```

- [ ] **Step 6: Add a "Tests" subsection under Commands, and a "Company info" subsection**

```markdown
### Tests

```bash
poetry run pytest -v              # full suite
poetry run pytest tests/test_gate.py -v   # single file
```

`tests/conftest.py` stubs every required `Settings` field via `os.environ.setdefault(...)` so test modules
can import `src.*` without a real `.env` — see its docstring before adding a new required (no-default)
field to `src/config.py`, or tests will start failing on collection.

### Company info

`src/assets/company_info.md` is the single source of truth for everything the `chat` node tells users about
the firm — services, pricing, required documents, contact/office/hours, FAQ — in all four supported
languages (en/uk/cs/ru). It's read fresh from disk on every `chat` turn (`nodes/chat.py::_read_company_info`),
so editing it takes effect on the very next message with no reload, restart, or deploy step. There is no
vector search or embeddings involved — the whole file is injected into the system prompt directly.
```

- [ ] **Step 7: Commit**

```bash
git add CLAUDE.md
git commit -m "docs: update CLAUDE.md for the gate/chat/lead_capture graph and company_info.md"
```

---

## Explicitly out of scope for this plan

- Booking/Google Calendar code (`state.py`'s booking-related settings, `schemas/ai/booking.py`) — untouched, unrelated to this refactor.
- `agent_rules/form_validator.py` and `agent_rules/date_format.py` — untouched apart from the one import-path fix in Task 8.
- The known `state.msg["ask_email"]` bug in `lead_capture.py`'s `_step_awaiting_email` (`AgentState` has no `msg` field) — pre-existing, unrelated to this refactor, not touched by any task above.
- `agent_rules/strings.py`'s `SERVICES_LIST_RESPONSE` (a short per-language service-name list `lead_capture._step_start` shows when no service was mentioned) duplicates service *names* (not pricing) with `company_info.md`. Left alone: it's a form-navigation prompt, not a factual claim, and touching it would mean editing `lead_capture.py`'s supporting strings, which Global Constraints keeps out of scope. Worth a follow-up if this bothers you.

from unittest.mock import AsyncMock, MagicMock, patch

from src.bots.tgbot.handlers.start import cmd_start


def _message(user_id=123, language_code="uk"):
    message = MagicMock()
    message.from_user.id = user_id
    message.from_user.language_code = language_code
    message.answer = AsyncMock()
    return message


async def test_cmd_start_resets_thread_state():
    """Regression, client-reported 2026-08-28: /start used to be a purely
    cosmetic welcome message that touched no conversation state at all - a
    client typing it expecting a clean slate (e.g. before testing a
    language switch) got no reset whatsoever. thread_id must match what
    handle_incoming uses for the same user (str(client_id), see
    bots/tgbot/handlers/message.py)."""
    message = _message(user_id=555)
    with patch(
        "src.bots.tgbot.handlers.start.reset_thread_state", new_callable=AsyncMock
    ) as reset:
        await cmd_start(message)
    reset.assert_awaited_once_with("555")
    message.answer.assert_awaited_once()


async def test_cmd_start_still_sends_welcome_if_reset_fails():
    """A reset failure must never swallow the welcome message itself - same
    defensive pattern as other non-critical side effects in this codebase
    (e.g. the removed gate.py _notify_human_request helper)."""
    message = _message(user_id=555)
    with patch(
        "src.bots.tgbot.handlers.start.reset_thread_state",
        new_callable=AsyncMock, side_effect=RuntimeError("boom"),
    ):
        await cmd_start(message)
    message.answer.assert_awaited_once()

from src.bots.tgbot.handlers.message import _markdown_bold_to_html


def test_converts_double_asterisk_bold_to_html_b_tags():
    assert _markdown_bold_to_html("Please provide your **Full Name**:") == (
        "Please provide your <b>Full Name</b>:"
    )


def test_converts_multiple_bold_spans():
    text = "- **30 minutes:** 1,900 CZK\n- **60 minutes:** 3,300 CZK"
    assert _markdown_bold_to_html(text) == (
        "- <b>30 minutes:</b> 1,900 CZK\n- <b>60 minutes:</b> 3,300 CZK"
    )


def test_leaves_plain_text_untouched():
    assert _markdown_bold_to_html("Just plain text, no formatting.") == (
        "Just plain text, no formatting."
    )


def test_escapes_html_special_characters_so_they_render_literally():
    assert _markdown_bold_to_html("Price < 5000 CZK & > 1000 CZK") == (
        "Price &lt; 5000 CZK &amp; &gt; 1000 CZK"
    )


def test_does_not_escape_quotes_telegram_would_show_literally():
    """Telegram's HTML mode only requires escaping &, <, > - html.escape's
    default of also escaping quotes to &quot; would show up as literal text
    in the message, since Telegram doesn't decode that entity back."""
    result = _markdown_bold_to_html('Type "no" to skip:')
    assert result == 'Type "no" to skip:'
    assert "&quot;" not in result

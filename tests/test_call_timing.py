from src.ai.conversation_agent.agent_rules.form_validator import FormValidator


def test_explicit_when_question_still_matches():
    assert FormValidator.is_asking_call_timing("коли ви зателефонуєте?") is True


def test_when_question_using_the_dzvon_call_root_now_matches():
    assert FormValidator.is_asking_call_timing("коли ви подзвоните?") is True


def test_call_request_pinned_to_weekend_day_now_matches_without_when_word():
    # Regression: a production test on 2026-08-27 sent "Подзвоніть мені в
    # суботу" ("Call me on Saturday") and it was missed entirely, for two
    # compounding reasons: (1) the call-word list only covered the
    # "телефон"/"звон" verb families ("зателефону", "позвон"), missing the
    # separate Ukrainian "дзвон" root ("подзвоніть", "передзвоніть") - now
    # added; (2) the check required an explicit "when"-word ("коли") even
    # when a weekend day was already named - now a call-word + weekend
    # mention matches without needing "when" too.
    assert FormValidator.is_asking_call_timing("Подзвоніть мені в суботу") is True


def test_call_request_without_weekend_or_when_word_does_not_match():
    assert FormValidator.is_asking_call_timing("Подзвоніть мені") is False


def test_weekend_mention_without_a_call_word_does_not_match():
    # Scope stays narrow: mentioning a weekend day alone (no call/contact
    # request) should not trigger the office-hours fast-path.
    assert FormValidator.is_asking_call_timing("Ми зустрінемось в суботу") is False


def test_english_call_request_pinned_to_saturday():
    assert FormValidator.is_asking_call_timing("Please call me on Saturday") is True


def test_no_text_does_not_match():
    assert FormValidator.is_asking_call_timing("") is False

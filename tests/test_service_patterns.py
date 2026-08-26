from src.ai.conversation_agent.agent_rules.form_validator import FormValidator


def test_detect_service_distinguishes_legal_from_visa_consultation():
    assert FormValidator.detect_service("потрібен юрист") == "legal_consultation"
    assert FormValidator.detect_service("I need a lawyer") == "legal_consultation"
    assert FormValidator.detect_service("právník") == "legal_consultation"
    assert FormValidator.detect_service("потрібна віза") == "visa_consultation"
    assert FormValidator.detect_service("migration consultation") == "visa_consultation"
    assert FormValidator.detect_service("міграційна консультація") == "visa_consultation"


def test_detect_service_bare_consultation_is_ambiguous():
    assert FormValidator.detect_service("потрібна консультація") == "consultation_ambiguous"
    assert FormValidator.detect_service("konzultace") == "consultation_ambiguous"
    assert FormValidator.detect_service("I need a consultation") == "consultation_ambiguous"


def test_detect_service_other_services_unaffected():
    assert FormValidator.detect_service("переклад документів") == "translation"
    assert FormValidator.detect_service("апостиль") == "apostille"
    assert FormValidator.detect_service("довіреність") == "poa"
    assert FormValidator.detect_service("щось незрозуміле xyz") is None

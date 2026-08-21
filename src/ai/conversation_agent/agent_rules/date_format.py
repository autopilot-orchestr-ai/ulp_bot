from datetime import datetime
from src.ai.conversation_agent.agent_rules.strings import _PRAGUE_TZ, _DAYS, _MONTHS

def fmt_prague(dt: datetime, lang: str = "cs") -> str:
    p = dt.astimezone(_PRAGUE_TZ)
    days = _DAYS.get(lang, _DAYS["en"])
    months = _MONTHS.get(lang, _MONTHS["en"])
    sep = "в" if lang in ("uk", "ru") else "v" if lang == "cs" else "at"
    return f"{days[p.weekday()]} {p.day}. {months[p.month - 1]} {sep} {p.strftime('%H:%M')}"


def format_slots(slots: list[datetime], lang: str = "cs") -> str:
    return "\n".join(f"  {i}. {fmt_prague(s, lang)}" for i, s in enumerate(slots, 1))


def format_slot(slot_iso: str, lang: str = "cs") -> str:
    return fmt_prague(datetime.fromisoformat(slot_iso), lang)
"""Stubs every Settings field that has no default, so `src.config.Settings()`
(instantiated at import time by nearly everything under src/) doesn't raise
a pydantic ValidationError when tests import project modules without a real
.env file. Pydantic-settings matches env var names case-insensitively, so
uppercase here matches the lowercase field names in src/config.py."""
import os

_TEST_ENV = {
    "CLIENT_NAME": "Test Client",
    "TELEGRAM_BOT_TOKEN": "test-token",
    "LLM_PROVIDER": "openai",
    "LLM_MODEL": "gpt-4o-mini",
    "OPENAI_API_KEY": "test-key",
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

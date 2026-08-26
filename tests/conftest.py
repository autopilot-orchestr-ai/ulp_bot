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

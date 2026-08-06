from pydantic_settings import BaseSettings
from dotenv import load_dotenv

load_dotenv()

class Settings(BaseSettings):
    # Client identity
    client_name: str

    # Token
    telegram_bot_token: str

    # DB
    db_url: str
    db_schema: str

    # LLM
    llm_provider: str
    llm_model: str
    openai_api_key: str

    # Embeddings
    embeddings_provider: str
    embeddings_model: str

    # Knowledge base
    faq_path: str

    # RAG tuning
    context_window: int
    retrieval_k: int
    similarity_threshold: float

    # Staff notifications
    staff_telegram_chat_id: str = ""
    staff_notify_email: str = ""

    # Google Calendar (BookingAgent)
    google_calendar_id: str
    google_service_account_json: str

    # Booking slot config
    # booking_days_ahead: int
    # booking_max_slots: int
    # booking_slot_duration_minutes: int
    # booking_working_hours_start: str
    # booking_working_hours_end: str
    # booking_working_days: str

    # SMTP (booking confirmation emails)
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str

    class Config:
        env_file = ".env"

settings = Settings()

def get_settings() -> Settings:
    return settings

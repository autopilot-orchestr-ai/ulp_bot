from datetime import datetime
from email.message import EmailMessage

import aiosmtplib

from src.logger import log_event
from src.ai.conversation_agent.data.strings import _PRAGUE_TZ
from src.config import settings


async def send_booking_confirmation(to_email: str,slot: datetime,client_name: str,) -> None:
    """Send a booking confirmation email. Skips with a log if SMTP is not configured."""
    if not settings.smtp_host:
        log_event("email_skipped", status="warn", reason="smtp_host not configured", to=to_email)
        return

    prague = slot.astimezone(_PRAGUE_TZ)
    slot_str = prague.strftime("%d.%m.%Y at %H:%M")

    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to_email
    message["Subject"] = "Consultation Confirmation — United Legal Partners"
    message.set_content(
        f"Dear {client_name},\n\n"
        f"Your consultation is tentatively scheduled for {slot_str} (Prague time).\n\n"
        f"To confirm your appointment, please complete your payment and send the receipt to office@ak-ulp.cz.\n\n"
        f"Address: Pařížská 127/20, Praha 1 – Josefov\n"
        f"Phone: +420 703 614 444\n"
        f"Email: office@ak-ulp.cz\n\n"
        f"Working hours: Mon–Fri 8:00–17:00\n\n"
        f"United Legal Partners s.r.o.\n"
    )

    log_event("email_sending", status="start", to=to_email, slot=slot_str)
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        log_event("email_sent", status="ok", to=to_email)
    except Exception as exc:
        log_event("email_sent", status="error", to=to_email, error=str(exc))
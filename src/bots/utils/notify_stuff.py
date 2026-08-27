from aiogram.types import User
from src.config import settings


async def notify_manager_lead_telegram(
    client_name: str,
    client_phone: str,
    client_email: str,
    service: str = "Other/Not specified",
    user: User | None = None,
    lang: str = "uk",
) -> None:
    """Notify manager when a client completes the lead capture form (Name, Phone, Email)."""
    chat_id = getattr(settings, "staff_telegram_chat_id", None) or getattr(settings, "STAFF_TELEGRAM_CHAT_ID", None)
    if not chat_id:
        return

    from src.bots.tgbot.bot import bot  # ✅ lazy import — breaks the cycle

    user_info = ""
    if user:
        user_mention = user.mention_html(user.full_name)
        username = f" (@{user.username})" if user.username else ""
        user_info = (
            f"👤 <b>Telegram акаунт:</b> {user_mention}{username}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
        )

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"🎯 <b>[НОВИЙ ЛІД] Клієнт залишив заявку!</b>\n\n"
            f"{user_info}"
            f"📛 <b>Ім'я / ПІБ:</b> {client_name}\n"
            f"📞 <b>Телефон:</b> <code>{client_phone}</code>\n"
            f"✉️ <b>Email:</b> {client_email}\n"
            f"🧾 <b>Послуга:</b> {service}\n"
            f"🌐 <b>Мова:</b> {lang.upper()}\n\n"
            f"👉 <i>Будь ласка, зв'яжіться з клієнтом для узгодження детальностей.</i>"
        ),
        parse_mode="HTML",
    )


async def notify_manager_media_telegram(user: User, content_type: str, lang: str) -> None:
    """Notify manager about received media files (documents, images, etc.)."""
    manager_chat_id = getattr(settings, "staff_telegram_chat_id", None) or getattr(settings, "STAFF_TELEGRAM_CHAT_ID", None)
    if not manager_chat_id:
        return

    from src.bots.tgbot.bot import bot  # ✅ lazy import

    user_mention = user.mention_html(user.full_name)
    username = f" (@{user.username})" if user.username else ""

    await bot.send_message(
        chat_id=manager_chat_id,
        text=(
            f"📎 <b>[ДОКУМЕНТ] Клієнт надіслав файл!</b>\n\n"
            f"👤 <b>Клієнт:</b> {user_mention}{username}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"📂 <b>Тип медіа:</b> {content_type.upper()}\n"
            f"🌐 <b>Визначена мова:</b> {lang.upper()}\n\n"
            f"👉 <i>Будь ласка, зв'яжіться з клієнтом для обробки документів.</i>"
        ),
        parse_mode="HTML",
    )


async def notify_manager_contacts_telegram(user: User, user_text: str) -> None:
    """Notify manager when client receives contact info."""
    manager_chat_id = getattr(settings, "staff_telegram_chat_id", None) or getattr(settings, "STAFF_TELEGRAM_CHAT_ID", None)
    if not manager_chat_id:
        return

    from src.bots.tgbot.bot import bot  # ✅ lazy import

    user_mention = user.mention_html(user.full_name)
    username = f" (@{user.username})" if user.username else ""

    await bot.send_message(
        chat_id=manager_chat_id,
        text=(
            f"🔔 <b>[КОНТАКТИ] Клієнт зацікавився послугами!</b>\n\n"
            f"👤 <b>Клієнт:</b> {user_mention}{username}\n"
            f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            f"💬 <b>Останній запит:</b> <i>\"{user_text}\"</i>\n\n"
            f"👉 <i>Клієнту було автоматично надіслано контакти для зв'язку.</i>"
        ),
        parse_mode="HTML",
    )


async def notify_manager_human_request_telegram(
    client_id: str,
    client_name: str | None,
    text: str,
    lang: str = "uk",
) -> None:
    """Notify manager immediately when a client explicitly asks to be
    contacted by a human, before the name/phone/email form is even filled
    in - contact details aren't known yet at this point, so staff need to
    open the chat themselves to respond. Complements
    notify_manager_lead_telegram, which fires later with full contact
    details once (and if) the client completes the form."""
    chat_id = getattr(settings, "staff_telegram_chat_id", None) or getattr(settings, "STAFF_TELEGRAM_CHAT_ID", None)
    if not chat_id:
        return

    from src.bots.tgbot.bot import bot  # lazy import — breaks the cycle

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"🙋 <b>[ЗАПИТ НА ЗВ'ЯЗОК] Клієнт хоче, щоб з ним зв'язались</b>\n\n"
            f"🆔 <b>Client ID:</b> <code>{client_id}</code>\n"
            f"📛 <b>Ім'я:</b> {client_name or 'Not specified'}\n"
            f"🌐 <b>Мова:</b> {lang.upper()}\n"
            f"💬 <b>Повідомлення:</b> <i>\"{text}\"</i>\n\n"
            f"👉 <i>Контактні дані ще не зібрані - можливо, варто написати клієнту самостійно.</i>"
        ),
        parse_mode="HTML",
    )


async def notify_manager_aggressive_telegram(
    client_id: str,
    client_name: str | None,
    text: str,
    lang: str = "uk",
) -> None:
    """Flag a hostile/aggressive client message for staff review. Non-blocking — the bot
    keeps answering the client normally regardless of this notification's outcome."""
    chat_id = getattr(settings, "staff_telegram_chat_id", None) or getattr(settings, "STAFF_TELEGRAM_CHAT_ID", None)
    if not chat_id:
        return

    from src.bots.tgbot.bot import bot  # lazy import — breaks the cycle

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"⚠️ <b>[АГРЕСИВНЕ ПОВІДОМЛЕННЯ] Клієнт написав щось грубе</b>\n\n"
            f"🆔 <b>Client ID:</b> <code>{client_id}</code>\n"
            f"📛 <b>Ім'я:</b> {client_name or 'Not specified'}\n"
            f"🌐 <b>Мова:</b> {lang.upper()}\n"
            f"💬 <b>Повідомлення:</b> <i>\"{text}\"</i>\n\n"
            f"👉 <i>Бот продовжує відповідати клієнту в звичайному режимі — це лише для вашої обізнаності.</i>"
        ),
        parse_mode="HTML",
    )


async def notify_staff_instagram() -> None:
    pass
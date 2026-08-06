from aiogram.types import User
from src.config import settings


async def notify_manager_lead_telegram(
    client_name: str,
    client_phone: str,
    client_email: str,
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
            f"🌐 <b>Мова:</b> {lang.upper()}\n\n"
            f"👉 <i>Будь ласка, зв'яжіться з клієнтом для узгодження детальностей.</i>"
        ),
        parse_mode="HTML",
    )


async def notify_staff_telegram(question_text: str) -> None:
    """Send a notification to staff via Telegram if configured (for escalations)."""
    chat_id = getattr(settings, "staff_telegram_chat_id", None) or getattr(settings, "STAFF_TELEGRAM_CHAT_ID", None)
    if not chat_id:
        return

    from src.bots.tgbot.bot import bot  # ✅ lazy import

    await bot.send_message(
        chat_id=chat_id,
        text=(
            f"⚠️ <b>[ЕСКАЛАЦІЯ] Неопрацьоване питання від клієнта:</b>\n\n"
            f"💬 <i>\"{question_text}\"</i>\n\n"
            f"👉 <i>Потрібне втручання менеджера.</i>"
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


async def notify_staff_instagram() -> None:
    pass
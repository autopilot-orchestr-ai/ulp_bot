from zoneinfo import ZoneInfo

_PRAGUE_TZ = ZoneInfo("Europe/Prague")

_DAYS = {
    "cs": ["pondělí", "úterý", "středa", "čtvrtek", "pátek", "sobota", "neděle"],
    "uk": ["понеділок", "вівторок", "середа", "четвер", "п'ятниця", "субота", "неділя"],
    "ru": ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"],
    "en": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"],
}

_DAY_MAP = {
    "MON": 0, "TUE": 1, "WED": 2, "THU": 3,
    "FRI": 4, "SAT": 5, "SUN": 6,
}

_MONTHS = {
    "cs": ["ledna", "února", "března", "dubna", "května", "června",
           "července", "srpna", "září", "října", "listopadu", "prosince"],
    "uk": ["січня", "лютого", "березня", "квітня", "травня", "червня",
           "липня", "серпня", "вересня", "жовтня", "листопада", "грудня"],
    "ru": ["января", "февраля", "марта", "апреля", "мая", "июня",
           "июля", "августа", "сентября", "октября", "ноября", "декабря"],
    "en": ["January", "February", "March", "April", "May", "June",
           "July", "August", "September", "October", "November", "December"],
}

_CZECH_CHARS = set("áčďéěíňóřšťúůýž")
_CZECH_WORDS = {"jo", "ano", "prosím", "ahoj", "chci", "mám", "zájem", "kde", "jak", "nabízíte", "strojkem"}
_UK_CHARS = set("іїєґІЇЄҐ")

_STRINGS = {
    "en": {
        "slots_intro": (
            "Here are the next available time slots:\n{slot_list}\n\n"
            "Which slot would you prefer? Just reply with the number."
        ),
        "no_slots": "I'm sorry, there are no available slots in the coming days. Please contact us directly at +420 703 614 444 or office@ak-ulp.cz.",
        "confirm_summary": (
            "Please review your booking request:\n"
            "  Consultation: {consultation_type} — {duration_minutes} min\n"
            "  Price: {price} CZK\n"
            "  Date: {slot_str}\n"
            "  Name: {name}\n"
            "  Phone: {phone}\n\n"
            "Shall I submit this request? (yes / no)"
        ),
        "booking_confirmed": (
            "Your slot for {slot_str} has been tentatively reserved.\n\n"
            "To confirm your appointment, please complete your payment of {price} CZK "
            "and send your receipt to office@ak-ulp.cz. "
            "A manager will confirm your slot within working hours (Mon–Fri 8:00–17:00)."
        ),
        "booking_cancelled": "No problem! Your request has been cancelled. Feel free to start over whenever you'd like to book.",
        "confirm_ambiguous": "Sorry, I didn't catch that. Please reply with yes to confirm or no to cancel.",
    },
    "cs": {
        "slots_intro": (
            "Zde jsou nejbližší volné termíny:\n{slot_list}\n\n"
            "Který termín vám vyhovuje? Odpovězte prosím číslem."
        ),
        "no_slots": "Omlouváme se, v nejbližších dnech nejsou volné termíny. Kontaktujte nás prosím na +420 703 614 444 nebo office@ak-ulp.cz.",
        "confirm_summary": (
            "Shrnutí vaší žádosti o konzultaci:\n"
            "  Konzultace: {consultation_type} — {duration_minutes} min\n"
            "  Cena: {price} Kč\n"
            "  Datum: {slot_str}\n"
            "  Jméno: {name}\n"
            "  Telefon: {phone}\n\n"
            "Mám žádost odeslat? (ano / ne)"
        ),
        "booking_confirmed": (
            "Váš termín {slot_str} byl předběžně rezervován.\n\n"
            "Pro potvrzení konzultace prosím uhraďte {price} Kč "
            "a zašlete doklad o platbě na office@ak-ulp.cz. "
            "Manažer potvrdí termín v pracovní době (Po–Pá 8:00–17:00)."
        ),
        "booking_cancelled": "V pořádku! Vaše žádost byla zrušena. Kdykoli budete chtít, začněte znovu.",
        "confirm_ambiguous": "Promiňte, nerozuměl/a jsem. Odpovězte prosím ano pro potvrzení nebo ne pro zrušení.",
    },
    "uk": {
        "slots_intro": (
            "Ось найближчі вільні терміни:\n{slot_list}\n\n"
            "Який термін вам підходить? Відповідайте, будь ласка, номером."
        ),
        "no_slots": "На жаль, у найближчі дні немає вільних місць. Зверніться до нас за телефоном +420 703 614 444 або на office@ak-ulp.cz.",
        "confirm_summary": (
            "Перевірте ваш запит на консультацію:\n"
            "  Консультація: {consultation_type} — {duration_minutes} хв\n"
            "  Вартість: {price} крон\n"
            "  Дата: {slot_str}\n"
            "  Ім'я: {name}\n"
            "  Телефон: {phone}\n\n"
            "Підтвердити запит? (так / ні)"
        ),
        "booking_confirmed": (
            "Ваш термін {slot_str} попередньо зарезервовано.\n\n"
            "Для підтвердження консультації, будь ласка, здійсніть оплату {price} крон "
            "та надішліть квитанцію на office@ak-ulp.cz. "
            "Менеджер підтвердить ваш запис у робочий час (пн–пт 8:00–17:00)."
        ),
        "booking_cancelled": "Добре! Ваш запит скасовано. Звертайтесь, коли захочете записатись знову.",
        "confirm_ambiguous": "Вибачте, не зрозумів/ла. Відповідайте, будь ласка, так для підтвердження або ні для скасування.",
    },
    "ru": {
        "slots_intro": (
            "Вот ближайшие доступные слоты:\n{slot_list}\n\n"
            "Какое время вам подходит? Ответьте, пожалуйста, номером."
        ),
        "no_slots": "К сожалению, в ближайшие дни нет свободных мест. Свяжитесь с нами по телефону +420 703 614 444 или на office@ak-ulp.cz.",
        "confirm_summary": (
            "Проверьте ваш запрос на консультацию:\n"
            "  Консультация: {consultation_type} — {duration_minutes} мин\n"
            "  Стоимость: {price} крон\n"
            "  Дата: {slot_str}\n"
            "  Имя: {name}\n"
            "  Телефон: {phone}\n\n"
            "Подтвердить запрос? (да / нет)"
        ),
        "booking_confirmed": (
            "Ваш слот {slot_str} предварительно зарезервирован.\n\n"
            "Для подтверждения консультации, пожалуйста, оплатите {price} крон "
            "и отправьте квитанцию на office@ak-ulp.cz. "
            "Менеджер подтвердит запись в рабочее время (пн–пт 8:00–17:00)."
        ),
        "booking_cancelled": "Хорошо! Ваш запрос отменён. Обращайтесь, когда захотите записаться снова.",
        "confirm_ambiguous": "Извините, не понял/а. Ответьте, пожалуйста, да для подтверждения или нет для отмены.",
    },
}

CANCEL_KEYWORDS = [
    "не зможу", "не приду", "скасувати", "відмінити",
    "не могу", "отменить", "cancel", "can't come", "cannot come",
]


MESSAGES = {
    "uk": {
        "start": "Чудово! Я з радістю передам вашу заявку менеджеру.\n\nБудь ласка, вкажіть ваше **Прізвище та Ім'я**:",
        "ask_phone": "Дякую, {name}! Тепер вкажіть ваш **номер телефону** для зв'язку:",
        "ask_email": "Прийнято! І останнє — вкажіть вашу **електронну пошту (Email)**:",
        "completed": "✅ Дякуємо! Усі дані отримано.\nНаш менеджер зв'яжеться з вами найближчим часом у робочі години."
    },
    "en": {
        "start": "Great! I will gladly forward your request to our manager.\n\nPlease enter your **Full Name**:",
        "ask_phone": "Thank you, {name}! Now, please provide your **phone number**:",
        "ask_email": "Got it! And lastly — please enter your **Email address**:",
        "completed": "✅ Thank you! All information has been received.\nOur manager will contact you shortly during working hours."
    },
    "cs": {
        "start": "Skvělé! Rádi předáme vaši žádost manažerovi.\n\nUveďte prosím vaše **Jméno a Příjmení**:",
        "ask_phone": "Děkujeme, {name}! Nyní prosím uveďte vaše **telefonní číslo**:",
        "ask_email": "Rozumím! A na závěr — uveďte prosím váš **E-mail**:",
        "completed": "✅ Děkujeme! Všechny údaje byly přijaty.\nNáš manažer vás bude brzy kontaktovat během pracovní doby."
    },
    "ru": {
        "start": "Отлично! Я с радостью передам вашу заявку менеджеру.\n\nПожалуйста, укажите ваше **Фамилию и Имя**:",
        "ask_phone": "Спасибо, {name}! Теперь укажите ваш **номер телефона** для связи:",
        "ask_email": "Принято! И последнее — укажите вашу **электронную почту (Email)**:",
        "completed": "✅ Спасибо! Все данные получены.\nНаш менеджер свяжется с вами в ближайшее время в рабочие часы."
    }
}
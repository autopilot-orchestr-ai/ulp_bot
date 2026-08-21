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
        "slots_intro": "Here are the next available time slots:\n{slot_list}\n\nWhich slot would you prefer? Just reply with the number.",
        "no_slots": "I'm sorry, there are no available slots in the coming days. Please contact us directly at +420 703 614 444 or office@ak-ulp.cz.",
        "confirm_summary": "Please review your booking request:\n  Consultation: {consultation_type} — {duration_minutes} min\n  Price: {price} CZK\n  Date: {slot_str}\n  Name: {name}\n  Phone: {phone}\n\nShall I submit this request? (yes / no)",
        "booking_confirmed": "Your slot for {slot_str} has been tentatively reserved.\n\nTo confirm your appointment, please complete your payment of {price} CZK and send your receipt to office@ak-ulp.cz. A manager will confirm your slot within working hours (Mon–Fri 8:00–17:00).",
        "booking_cancelled": "No problem! Your request has been cancelled. Feel free to start over whenever you'd like to book.",
        "confirm_ambiguous": "Sorry, I didn't catch that. Please reply with yes to confirm or no to cancel.",
    },
    "cs": {
        "slots_intro": "Zde jsou nejbližší volné termíny:\n{slot_list}\n\nKterý termín vám vyhovuje? Odpovězte prosím číslem.",
        "no_slots": "Omlouváme se, v nejbližších dnech nejsou volné termíny. Kontaktujte nás prosím na +420 703 614 444 nebo office@ak-ulp.cz.",
        "confirm_summary": "Shrnutí vaší žádosti o konzultaci:\n  Konzultace: {consultation_type} — {duration_minutes} min\n  Cena: {price} Kč\n  Datum: {slot_str}\n  Jméno: {name}\n  Telefon: {phone}\n\nMám žádost odeslat? (ano / ne)",
        "booking_confirmed": "Váš termín {slot_str} byl předběžně rezervován.\n\nPro potvrzení konzultace prosím uhraďte {price} Kč a zašlete doklad o platbě na office@ak-ulp.cz. Manažer potvrdí termín v pracovní době (Po–Pá 8:00–17:00).",
        "booking_cancelled": "V pořádku! Vaše žádost byla zrušena. Kdykoli budete chtít, začněte znovu.",
        "confirm_ambiguous": "Promiňte, nerozuměl/a jsem. Odpovězte prosím ano pro potvrzení nebo ne pro zrušení.",
    },
    "uk": {
        "slots_intro": "Ось найближчі вільні терміни:\n{slot_list}\n\nЯкий термін вам підходить? Відповідайте, будь ласка, номером.",
        "no_slots": "На жаль, у найближчі дні немає вільних місць. Зверніться до нас за телефоном +420 703 614 444 або на office@ak-ulp.cz.",
        "confirm_summary": "Перевірте ваш запит на консультацію:\n  Консультація: {consultation_type} — {duration_minutes} хв\n  Вартість: {price} крон\n  Дата: {slot_str}\n  Ім'я: {name}\n  Телефон: {phone}\n\nПідтвердити запит? (так / ні)",
        "booking_confirmed": "Ваш термін {slot_str} попередньо зарезервовано.\n\nДля підтвердження консультації, будь ласка, здійсніть оплату {price} крон та надішліть квитанцію на office@ak-ulp.cz. Менеджер підтвердить ваш запис у робочий час (пн–пт 8:00–17:00).",
        "booking_cancelled": "Добре! Ваш запит скасовано. Звертайтесь, коли захочете записатись знову.",
        "confirm_ambiguous": "Вибачте, не зрозумів/ла. Відповідайте, будь ласка, так для підтвердження або ні для скасування.",
    },
    "ru": {
        "slots_intro": "Вот ближайшие доступные слоты:\n{slot_list}\n\nКакое время вам подходит? Ответьте, пожалуйста, номером.",
        "no_slots": "К сожалению, в ближайшие дни нет свободных мест. Свяжитесь с нами по телефону +420 703 614 444 или на office@ak-ulp.cz.",
        "confirm_summary": "Проверьте ваш запрос на консультацию:\n  Консультация: {consultation_type} — {duration_minutes} мин\n  Стоимость: {price} крон\n  Дата: {slot_str}\n  Имя: {name}\n  Телефон: {phone}\n\nПодтвердить запрос? (да / нет)",
        "booking_confirmed": "Ваш слот {slot_str} предварительно зарезервирован.\n\nДля подтверждения консультации, пожалуйста, оплатите {price} крон и отправьте квитанцию на office@ak-ulp.cz. Менеджер подтвердит запись в рабочее время (пн–пт 8:00–17:00).",
        "booking_cancelled": "Хорошо! Ваш запрос отменён. Обращайтесь, когда захотите записаться снова.",
        "confirm_ambiguous": "Извините, не понял/а. Ответьте, пожалуйста, да для подтверждения или нет для отмены.",
    },
}

# --- Service & Intent Patterns ---

SERVICE_PATTERNS = {
    r'кон[сзм][уь]?ль?т': "Консультація",
    r'переклад': "Судові переклади",
    r'довір': "Довіреність",
    r'апостил': "Апостиль",
    r'заяв': "Офіційні заяви",
    r'несудим': "Довідка про несудимість",
    r'одруж|брак|шлюб': "Супровід при одруженні",
    r'дублікат': "Дублікати документів",
}

QUESTION_PATTERNS = [
    # General symbols
    r'\?', 
    # English
    r'\bhow\b', r'\bwhat\b', r'\bwhen\b', r'\bwhere\b', r'\bwhy\b', r'\bwho\b', 
    r'\bprice\b', r'\bcost\b', r'\bmuch\b',
    # Ukrainian / Russian
    r'\bякі\b', r'\bякісь\b', r'\bскільки\b', r'\bціна\b', r'\bвартість\b',
    r'\bумови\b', r'\bде\b', r'\bяк\b', r'\bщо\b', r'\bкогда\b', r'\bкакие\b',
    r'\bсколько\b', r'\bцена\b', r'\bстоимость\b', r'\bрасскажите\b', r'\bрозкажіть\b',
    # Czech
    r'\bjak\b', r'\bkde\b', r'\bkolik\b', r'\bcena\b', r'\bproč\b', r'\bkdy\b'
]

INTENT_KEYWORDS = [
    # English
    "hello", "hi", "hey", "need", "want", "please", "book", "consultation",
    # Ukrainian / Russian
    "треба", "хочу", "потрібно", "цікавит", "запишіть", "подзвоніть", 
    "передзвоніть", "добрий", "привіт", "доброго", "підкажіть", "послуга",
    # Czech
    "chci", "potřebuji", "prosím", "ahoj", "dobrý"
]

# --- Profanity & Hostility Patterns ---
PROFANITY_PATTERNS = [
    r'\bблят[ьа]?\b', r'\bсука\b', r'\bнах[ууі]й\b', r'\bхуй\b', r'\bпизд[аеыоуя]?\b',
    r'\bебат[ьъ]\b', r'\bєбат[ьi]\b', r'\bдолбо[еє]б\b', r'\bтуп[оыій]+[ая]?\b',
    r'\bfuck\b', r'\bshit\b', r'\basshole\b', r'\bbitch\b'
]

# --- Human Handoff / Urgency Patterns ---
HUMAN_HANDOFF_PATTERNS = [
    r'\bподзвон[иі]ть?\b', r'\bнапиш[iі]ть?\b', r'\bзв\'яж\w+\b', r'\bменеджер\w*\b', 
    r'\bтерміново\b', r'\bсрочно\b', r'\bшвидко\b'
]
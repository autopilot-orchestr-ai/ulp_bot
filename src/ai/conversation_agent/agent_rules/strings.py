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
    r'\bподзвон[иі]ть?\b', r'\bнапиш[iі]ть?\b', r'\bзв\'яж[iі]ться\b',
    r'\bпоклич[iі]ть?\b', r'\bоператор\b', r'\bменеджер\b', r'\bлюдина\b',
    r'\bпрямо зараз\b', r'\bтерм[іi]ново\b', r'\bсрочно\b'
]

# --- System Responses ---
HUMAN_HANDOFF_RESPONSE = {
    "uk": "Зрозумів! Я передав ваше повідомлення менеджеру. Він зв'яжеться з вами в найближчий час.",
    "cs": "Rozumím! Předal jsem vaši zprávu manažerovi. Brzy se s vámi spojí.",
    "en": "Understood! I have forwarded your request to our manager. They will contact you shortly.",
    "ru": "Понял! Я передал ваше сообщение менеджеру. Он свяжется с вами в ближайшее время."
}

CANCEL_KEYWORDS = [
    "не зможу", "не приду", "скасувати", "відмінити", "відміна", "стоп",
    "не могу", "отменить", "отмена", "не надо", "передумав", "передумал",
    "cancel", "can't come", "cannot come", "не треба", "закрити", "не хочу"
]

WEEKEND_KEYWORDS = [
    "субот", "неділ", "суббот", "воскрес", "вихідн", "выходн",
    "sobot", "neděl", "víkend", "saturday", "sunday", "weekend"
]

# --- Bot Replies & Form Prompts ---

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

WEEKEND_NOTICES = {
    "en": "⚠️ **Please note:** our office is open Monday to Friday. We are closed on weekends (Saturday and Sunday), but our team will contact you during working hours to schedule a convenient day!\n\n",
    "cs": "⚠️ **Upozornění:** naše kancelář má otevřeno od pondělí do pátku. O víkendech (sobota a neděle) máme zavřeno, ale náš tým vás bude kontaktovat v pracovní době, abychom domluvili vyhovující den!\n\n",
    "uk": "⚠️ **Зверніть увагу:** наш офіс працює з понеділка по п'ятницю. У вихідні (субота та неділя) ми зачинені, але наша команда зв'яжеться з Вами в робочий час для узгодження зручного дня!\n\n",
    "ru": "⚠️ **Обратите внимание:** наш офис работает с понедельника по пятницу. В выходные (суббота и воскресенье) мы закрыты, но наша команда свяжется с Вами в рабочее время для согласования удобного дня!\n\n",
}

PHONE_REPROMPT = {
    "en": "Please provide a **valid phone number** to contact you (e.g.: +420 123 456 789):",
    "cs": "Uveďte prosím **platné telefonní číslo** pro kontakt (např.: +420 123 456 789):",
    "uk": "Будь ласка, вкажіть **дійсний номер телефону** для зв'язку (наприклад: +420 123 456 789 або 097 123 4567):",
    "ru": "Пожалуйста, укажите **действительный номер телефона** для связи (например: +420 123 456 789):",
}

EMAIL_REPROMPT = {
    "en": "Please provide a **valid Email** (e.g.: name@gmail.com) or type **'no'** if you prefer not to provide one:",
    "cs": "Uveďte prosím **platný e-mail** (např.: name@gmail.com) nebo napište **'ne'**, pokud e-mail nechcete zadat:",
    "uk": "Будь ласка, вкажіть **коректний Email** (наприклад: name@gmail.com) або напишіть **'ні'**, якщо не бажаєте вказувати пошту:",
    "ru": "Пожалуйста, укажите **корректный Email** (например: name@gmail.com) или напишите **'нет'**, если не хотите указывать почту:",
}

NAME_REPROMPT = {
    "en": "Please provide your real **First and Last Name** (e.g.: Alexander Voroniuk):",
    "cs": "Uveďte prosím své skutečné **Jméno a Příjmení** (např.: Alexandr Voroniuk):",
    "uk": "Будь ласка, вкажіть ваше справжнє **Прізвище та Ім'я** (наприклад: Олександр Воронюк):",
    "ru": "Пожалуйста, укажите ваше настоящее **Имя и Фамилию** (например: Александр Воронюк):",
}
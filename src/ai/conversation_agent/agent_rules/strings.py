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

# --- Service & Intent Patterns ---

# Maps multilingual regex matches to a standard Internal ID
SERVICE_PATTERNS = {
    # ⚖️ Legal consultations - distinct from visa/migration below (used to
    # be one conflated "consultation" bucket; a client reported the bot
    # never asking which type was meant).
    r'юрист|юридич|юридическ|právník|pravnik|advokát|advokat|lawyer|адвокат|právní|\blegal\b': "legal_consultation",
    # 🛂 Visa / migration consultations.
    r'віз|виз|víz|viz|visa|мігра|миграц|migra|migrant': "visa_consultation",
    # A bare "consultation" with neither legal nor visa qualifier - genuinely
    # ambiguous, handled by nodes/lead_capture.py's awaiting_consultation_type
    # step (asks which type before showing pricing).
    r'кон[сзм][уь]?ль?т|konzultac|consult|poradenstv': "consultation_ambiguous",

    r'переклад|перевод|překlad|preklad|translat': "translation",
    r'довір|довер|pln[aeáé]\s?moc|plnou\s?moc|power\s?of\s?attorney': "poa",
    r'апостил|apostil': "apostille",
    r'заяв|згод|согласи|prohlášen|prohlasen|souhlas|statement|consent': "statement",
    r'несудим|trest|rejstřík|rejstrik|police\s?clearance|criminal': "police_clearance",
    r'одруж|брак|шлюб|свадьб|sňatk|snatk|svatb|marriag|weddin': "marriage",
    r'дублікат|дубликат|duplikát|duplikat|duplicat': "duplicates",
}

# Translates the Internal ID back to the correct language for the bot's response
SERVICE_LOCALIZED_NAMES = {
    "legal_consultation": {"uk": "Юридичні консультації", "ru": "Юридические консультации", "cs": "Právní konzultace", "en": "Legal Consultations"},
    "visa_consultation": {"uk": "Візові консультації", "ru": "Визовые консультации", "cs": "Vízové konzultace", "en": "Visa Consultations"},
    "translation": {"uk": "Судові переклади", "ru": "Судебные переводы", "cs": "Soudní překlady", "en": "Sworn Translations"},
    "poa": {"uk": "Довіреності", "ru": "Доверенности", "cs": "Plné moci", "en": "Powers of Attorney"},
    "apostille": {"uk": "Апостиль", "ru": "Апостиль", "cs": "Apostila", "en": "Apostille"},
    "statement": {"uk": "Офіційні заяви", "ru": "Официальные заявления", "cs": "Úřední prohlášení", "en": "Official Statements"},
    "police_clearance": {"uk": "Довідка про несудимість", "ru": "Справка о несудимости", "cs": "Výpis z rejstříku trestů", "en": "Police Clearance Certificate"},
    "marriage": {"uk": "Супровід при одруженні", "ru": "Сопровождение при бракосочетании", "cs": "Asistence při sňatku", "en": "Marriage Support"},
    "duplicates": {"uk": "Дублікати документів", "ru": "Дубликаты документов", "cs": "Duplikáty dokumentů", "en": "Document Duplicates"},
    "consultation_ambiguous": {"uk": "Консультації", "ru": "Консультации", "cs": "Konzultace", "en": "Consultations"},
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
    r'(?i)блят[ьа]?', r'(?i)сука', r'(?i)нах[ууі]й', r'(?i)х[уюї]й', r'(?i)п[иі]зд[аеыоуя]?',
    r'(?i)[єес]бат[ьiъ]?', r'(?i)долбо[еє]б', r'(?i)\bтуп[аоыіеє]+[ая]?\b',
    r'(?i)fuck', r'(?i)shit', r'(?i)asshole', r'(?i)bitch',
    r'(?i)kurv[aae]', r'(?i)prdel', r'(?i)kokot', r'(?i)zmrd'
]

# --- Human Handoff / Urgency Patterns ---
HUMAN_HANDOFF_PATTERNS = [
    r'\bподзвон[иі]ть?\b', r'\bнапиш[iі]ть?\b', r'\bзв\'яж\w+\b', r'\bменеджер\w*\b', 
    r'\bтерміново\b', r'\bсрочно\b', r'\bшвидко\b'
]

# --- System Responses ---
HUMAN_HANDOFF_RESPONSE = {
    "uk": "Зрозумів! Я передав ваше повідомлення менеджеру. Він зв'яжеться з вами в найближчий час.",
    "cs": "Rozumím! Předal jsem vaši zprávu manažerovi. Brzy se s vámi spojí.",
    "en": "Understood! I have forwarded your request to our manager. They will contact you shortly.",
    "ru": "Понял! Я передал ваше сообщение менеджеру. Он свяжется с вами в ближайшее время."
}

CANCEL_KEYWORDS = [
    "не зможу", "не приду", "скасувати", "скасуйте", "скасуй", "відмінити",
    "відміните", "відміни", "відміна", "стоп",
    "не могу", "отменить", "отмените", "отмени", "отмена", "не надо", "передумав", "передумал",
    "cancel", "can't come", "cannot come", "не треба", "закрити", "не хочу",
    "zrušte", "zruš", "zrušit"
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

# Per user policy (2026-08-27): no callback promise here - this notice is
# followed directly by HANDOFF_MESSAGES (see chat.py / lead_capture.py),
# which already tells the client how to reach the firm themselves.
WEEKEND_NOTICES = {
    "en": "⚠️ **Please note:** our office is open Monday to Friday. We are closed on weekends (Saturday and Sunday).\n\n",
    "cs": "⚠️ **Upozornění:** naše kancelář má otevřeno od pondělí do pátku. O víkendech (sobota a neděle) máme zavřeno.\n\n",
    "uk": "⚠️ **Зверніть увагу:** наш офіс працює з понеділка по п'ятницю. У вихідні (субота та неділя) ми зачинені.\n\n",
    "ru": "⚠️ **Обратите внимание:** наш офис работает с понедельника по пятницу. В выходные (суббота и воскресенье) мы закрыты.\n\n",
}

PHONE_REPROMPT = {
    "en": "Please provide a **valid phone number** to contact you (e.g.: +420 123 456 789):",
    "cs": "Uveďte prosím **platné telefonní číslo** pro kontakt (např.: +420 123 456 789):",
    "uk": "Будь ласка, вкажіть **дійсний номер телефону** для зв'язку (наприклад: +420 123 456 789 або 097 123 4567):",
    "ru": "Пожалуйста, укажите **действительный номер телефона** для связи (например: +420 123 456 789):",
}

NAME_REPROMPT = {
    "en": "Please provide your real **First and Last Name** (e.g.: Peter Parker):",
    "cs": "Uveďte prosím své skutečné **Jméno a Příjmení** (např.: Honza Novakov):",
    "uk": "Будь ласка, вкажіть ваше справжнє **Прізвище та Ім'я** (наприклад: Іван Іваненко):",
    "ru": "Пожалуйста, укажите ваше настоящее **Имя и Фамилию** (например: Петр Петров):",
}

EMAIL_REPROMPT = {
    "en": "Please provide a **valid email address** (e.g.: name@example.com), or type \"no\" to skip:",
    "cs": "Uveďte prosím **platnou e-mailovou adresu** (např.: jmeno@example.com), nebo napište \"ne\" pro přeskočení:",
    "uk": "Будь ласка, вкажіть **дійсну електронну адресу** (наприклад: imya@example.com), або напишіть «ні», щоб пропустити:",
    "ru": "Пожалуйста, укажите **действительный адрес электронной почты** (например: imya@example.com), или напишите «нет», чтобы пропустить:",
}

CONSULTATION_TYPE_PROMPT = {
    "en": "Would you like a **Legal Consultation** or a **Visa/Migration Consultation**?",
    "cs": "Chcete **právní konzultaci**, nebo **vízovou/migrační konzultaci**?",
    "uk": "Вас цікавить **юридична консультація** чи **візова/міграційна консультація**?",
    "ru": "Вас интересует **юридическая консультация** или **визовая/миграционная консультация**?",
}

CONTACT_CONFIRMATION_PROMPT = {
    "en": "Would you like our manager to contact you to arrange this? **Yes** or **No**.",
    "cs": "Přejete si, aby vás kontaktoval náš manažer kvůli vyřízení tohoto požadavku? **Ano**, nebo **Ne**.",
    "uk": "Чи бажаєте, щоб з Вами зв'язався наш менеджер для оформлення запиту? **Так** або **Ні**.",
    "ru": "Хотите, чтобы с Вами связался наш менеджер для оформления запроса? **Да** или **Нет**.",
}

CONTACT_DECLINED_MESSAGE = {
    "en": "No problem at all! Feel free to reach out anytime if you have questions. 😊",
    "cs": "Žádný problém! Pokud budete mít jakékoli dotazy, neváhejte se kdykoli ozvat. 😊",
    "uk": "Добре, немає проблем! Якщо виникнуть питання — звертайтесь у будь-який час. 😊",
    "ru": "Хорошо, никаких проблем! Если возникнут вопросы — обращайтесь в любое время. 😊",
}

SERVICES_LIST_RESPONSE = {
    "uk": "Ось перелік послуг, які ми надаємо:\n\n⚖️ **Юридичні консультації**\n🛂 **Візові консультації**\n📄 **Завірені судові переклади**\n🔏 **Апостиль документів**\n📑 **Складення довіреностей**\n✍️ **Офіційні заяви** (згода на виїзд, спадщина)\n🏛️ **Довідка про несудимість з України**\n💍 **Супровід при одруженні в Чехії**\n🗂️ **Дублікати документів з України**\n\nЯка саме послуга вас цікавить?",
    "ru": "Вот перечень услуг, которые мы предоставляем:\n\n⚖️ **Юридические консультации**\n🛂 **Визовые консультации**\n📄 **Заверенные судебные переводы**\n🔏 **Апостиль документов**\n📑 **Составление доверенностей**\n✍️ **Официальные заявления** (согласие на выезд, наследство)\n🏛️ **Справка об отсутствии судимости из Украины**\n💍 **Сопровождение при бракосочетании в Чехии**\n🗂️ **Дубликаты документов из Украины**\n\nКакая именно услуга вас интересует?",
    "cs": "Zde je seznam služeb, které poskytujeme:\n\n⚖️ **Právní konzultace**\n🛂 **Vízové konzultace**\n📄 **Soudní překlady**\n🔏 **Apostila**\n📑 **Plné moci**\n✍️ **Oficiální prohlášení** (souhlas s cestou, dědictví)\n🏛️ **Výpis z rejstříku trestů z Ukrajiny**\n💍 **Asistence při sňatku**\n🗂️ **Duplikáty dokumentů z Ukrajiny**\n\nO jakou službu máte zájem?",
    "en": "Here is the list of services we provide:\n\n⚖️ **Legal Consultations**\n🛂 **Visa Consultations**\n📄 **Certified Translations**\n🔏 **Apostille**\n📑 **Powers of Attorney**\n✍️ **Official Statements** (child travel consent, inheritance)\n🏛️ **Police Clearance Certificate from Ukraine**\n💍 **Marriage Support Package**\n🗂️ **Document Duplicates from Ukraine**\n\nWhich service are you interested in?"
}

WORKING_HOURS_MSG = {
    "uk": "З Вами зв'яжуться в найкоротші строки під час нашого робочого дня з понеділка по п'ятницю між 8:00 та 17:00.",
    "cs": "Budeme vás kontaktovat co nejdříve během naší pracovní doby od pondělí do pátku mezi 8:00 a 17:00.",
    "en": "You will be contacted as soon as possible during our working hours, Monday to Friday between 8:00 AM and 5:00 PM.",
    "ru": "С вами свяжутся в кратчайшие сроки в течение нашего рабочего дня с понедельника по пятницу с 8:00 до 17:00."
}

SUCCESS_MESSAGE = {
    "uk": "✅ Дякуємо! Усі дані отримано. Наш менеджер зв'яжеться з вами найближчим часом у робочі години.",
    "ru": "✅ Спасибо! Все данные получены. Наш менеджер свяжется с вами в ближайшее время в рабочие часы.",
    "cs": "✅ Děkujeme! Všechny údaje byly přijaty. Náš manažer vás bude brzy kontaktovat během pracovní doby.",
    "en": "✅ Thank you! All details have been received. Our manager will contact you shortly during working hours."
}
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
    "en": "Please provide your real **First and Last Name** (e.g.: Peter Parker):",
    "cs": "Uveďte prosím své skutečné **Jméno a Příjmení** (např.: Honza Novakov):",
    "uk": "Будь ласка, вкажіть ваше справжнє **Прізвище та Ім'я** (наприклад: Іван Іваненко):",
    "ru": "Пожалуйста, укажите ваше настоящее **Имя и Фамилию** (например: Петр Петров):",
}

SERVICES_LIST_RESPONSE = {
    "uk": "Ось перелік послуг, які ми надаємо:\n\n1. **Юридичні консультації**\n2. **Візові консультації**\n3. **Судові переклади**\n4. **Апостиль**\n5. **Довіреності**\n6. **Офіційні заяви**\n7. **Довідка про несудимість з України**\n8. **Супровід при одруженні**\n9. **Дублікати документів з України**\n\nЯка саме послуга вас цікавить?",
    "ru": "Вот перечень услуг, которые мы предоставляем:\n\n1. **Юридические консультации**\n2. **Визовые консультации**\n3. **Судебные переводы**\n4. **Апостиль**\n5. **Доверенности**\n6. **Официальные заявления**\n7. **Справка о несудимости из Украины**\n8. **Сопровождение при бракосочетании**\n9. **Дубликаты документов из Украины**\n\nКакая именно услуга вас интересует?",
    "cs": "Zde je seznam služeb, které poskytujeme:\n\n1. **Právní poradenství**\n2. **Vízové poradenství**\n3. **Soudní překlady**\n4. **Apostila**\n5. **Plné moci**\n6. **Úřední prohlášení**\n7. **Výpis z rejstříku trestů z Ukrajiny**\n8. **Asistence při sňatku**\n9. **Duplikáty dokumentů z Ukrajiny**\n\nO jakou službu máte zájem?",
    "en": "Here is the list of services we provide:\n\n1. **Legal Consultations**\n2. **Visa Consultations**\n3. **Sworn Translations**\n4. **Apostille**\n5. **Powers of Attorney**\n6. **Official Statements**\n7. **Police Clearance Certificate from Ukraine**\n8. **Marriage Support**\n9. **Document Duplicates from Ukraine**\n\nWhich service are you interested in?"
}

WORKING_HOURS_MSG = {
    "uk": "З Вами зв'яжуться в найкоротші строки під час нашого робочого дня з понеділка по п'ятницю між 8:00 та 17:00.",
    "cs": "Budeme vás kontaktovat co nejdříve během naší pracovní doby od pondělí do pátku mezi 8:00 a 17:00.",
    "en": "You will be contacted as soon as possible during our working hours, Monday to Friday between 8:00 AM and 5:00 PM.",
    "ru": "С вами свяжутся в кратчайшие сроки в течение нашего рабочего дня с понедельника по пятницу с 8:00 до 17:00."
}
import asyncio
import logging
import os
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import aiosqlite

from aiogram import Bot, Dispatcher, F
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    CallbackQuery,
)

# ============================================================
# 0. LOCALES
# ============================================================

LOCALES = {
    "ru": {
        "welcome": (
            "Здравствуйте! Это бот <b>EYUF</b>.\n\n"
            "Выберите язык / Tilni tanlang / Select language:"
        ),
        "lang_selected": (
            "Выбран русский язык 🇷🇺\n\n"
            "Для заполнения анкеты нажмите кнопку ниже."
        ),
        "btn_fill": "📝 Заполнить анкету",
        "btn_change_lang": "🌐 Сменить язык",
        "btn_pending": "📋 Неотвеченные анкеты",
        "fill_instructions": (
            "Скопируйте шаблон ниже (нажмите на него, чтобы скопировать), "
            "заполните все пункты после двоеточия и отправьте <b>одним сообщением</b>:\n\n"
            "{template}\n\n"
            "Пример заполненной строки:\n"
            "<code>Full Name: John Michael Smith</code>"
        ),
        "not_text": "Пожалуйста, отправьте анкету текстом, используя шаблон выше.",
        "missing_fields": (
            "❗ Не все пункты заполнены. Не хватает:\n\n"
            "{missing_text}\n\n"
            "Скопируйте шаблон заново, заполните все пункты после двоеточия и отправьте одним сообщением:\n\n"
            "{template}"
        ),
        "prompt_university": "🏛️ Отлично! Теперь введите <b>название университета</b> (University):",
        "prompt_offer_letter": "📄 Пожалуйста, отправьте <b>Offer Letter</b> (файлом/документом):",
        "not_a_document": "⚠️ Пожалуйста, отправьте файл/документ с Offer Letter.",
        "app_submitted": (
            "✅ <b>Анкета успешно отправлена!</b>\n\n"
            "Пожалуйста, дождитесь ответа администратора. "
            "Вы сможете отправлять сообщения после того, как админ ответит вам."
        ),
        "wait_for_admin": "⏳ Ваша анкета находится на рассмотрении. Пожалуйста, дождитесь ответа администратора.",
        "doc_received_caption": (
            "📄 <b>Ваш документ</b>\n\n"
            "Документ был отправлен администратором."
        ),
        "msg_received_prefix": "💬 <b>Сообщение от администратора:</b>\n\n",
        "btn_send_file": "📄 Отправить файл",
        "btn_send_msg": "💬 Отправить сообщение",
        "admin_prompt_file": (
            "📎 Теперь отправьте <b>файл</b> сюда.\n\n"
            "Получатель: <b>{name}</b>\n"
            "Telegram ID: <code>{tg_id}</code>\n\n"
            "Для отмены: /cancel"
        ),
        "admin_prompt_msg": (
            "💬 Введите <b>текстовое сообщение</b> для пользователя.\n\n"
            "Получатель: <b>{name}</b>\n"
            "Telegram ID: <code>{tg_id}</code>\n\n"
            "Для отмены: /cancel"
        ),
        "file_sent_success": "✅ Файл успешно отправлен пользователю.",
        "file_sent_error": "❌ Не удалось отправить файл пользователю.",
        "msg_sent_success": "✅ Сообщение успешно отправлено пользователю.",
        "msg_sent_error": "❌ Не удалось отправить сообщение пользователю.",
        "cancelled": "Операция отменена.",
        "pending_empty": "🎉 Все анкеты обработаны! Неотвеченных нет.",
        "pending_title": "📋 <b>Список неотвеченных анкет ({count}):</b>",
        "app_card_title": "📥 <b>НЕОТВЕЧЕННАЯ АНКЕТА №{app_id}</b>"
    },
    "uz": {
        "welcome": (
            "Assalomu alaykum! Bu <b>EYUF</b> boti.\n\n"
            "Tilni tanlang / Выберите язык / Select language:"
        ),
        "lang_selected": (
            "O'zbek tili tanlandi 🇺🇿\n\n"
            "Anketani to'ldirish uchun pastdagi tugmani bosing."
        ),
        "btn_fill": "📝 Anketani to'ldirish",
        "btn_change_lang": "🌐 Tilni o'zgartirish",
        "btn_pending": "📋 Javob berilmagan anketalar",
        "fill_instructions": (
            "Pastroqdagi shablonni nusxalang (nusxalash uchun ustiga bosing), "
            "ikki nuqtadan so'ng barcha punktlarni to'ldiring va <b>bitta xabar bilan</b> yuboring:\n\n"
            "{template}\n\n"
            "To'ldirilgan qatorga misol:\n"
            "<code>Full Name: John Michael Smith</code>"
        ),
        "not_text": "Iltimos, anketani yuqoridagi shablondan foydalanib matn ko'rinishida yuboring.",
        "missing_fields": (
            "❗ Barcha punktlar to'ldirilmagan. Yetishmayapti:\n\n"
            "{missing_text}\n\n"
            "Shablonni qayta nusxalang, barcha punktlarni to'ldiring va bitta xabar bilan yuboring:\n\n"
            "{template}"
        ),
        "prompt_university": "🏛️ Ajoyib! Endi <b>universitet nomini</b> kiriting (University):",
        "prompt_offer_letter": "📄 Iltimos, <b>Offer Letter</b> hujjatini yuboring (fayl ko'rinishida):",
        "not_a_document": "⚠️ Iltimos, Offer Letter hujjatini fayl shaklida yuboring.",
        "app_submitted": (
            "✅ <b>Anketa muvaffaqiyatli yuborildi!</b>\n\n"
            "Iltimos, administrator javobini kuting. "
            "Admin javob bergandan so'ng xabar yuborishingiz mumkin bo'ladi."
        ),
        "wait_for_admin": "⏳ Anketangiz ko'rib chiqilmoqda. Iltimos, administrator javobini kuting.",
        "doc_received_caption": (
            "📄 <b>Sizning hujjatingiz</b>\n\n"
            "Hujjat administrator tomonidan yuborildi."
        ),
        "msg_received_prefix": "💬 <b>Administratordan xabar:</b>\n\n",
        "btn_send_file": "📄 Fayl yuborish",
        "btn_send_msg": "💬 Xabar yuborish",
        "admin_prompt_file": (
            "📎 Endi bu yerga <b>faylni</b> yuboring.\n\n"
            "Qabul qiluvchi: <b>{name}</b>\n"
            "Telegram ID: <code>{tg_id}</code>\n\n"
            "Bekor qilish uchun: /cancel"
        ),
        "admin_prompt_msg": (
            "💬 Foydalanuvchi uchun <b>matnli xabarni</b> kiriting.\n\n"
            "Qabul qiluvchi: <b>{name}</b>\n"
            "Telegram ID: <code>{tg_id}</code>\n\n"
            "Bekor qilish uchun: /cancel"
        ),
        "file_sent_success": "✅ Fayl foydalanuvchiga muvaffaqiyatli yuborildi.",
        "file_sent_error": "❌ Faylni foydalanuvchiga yuborib bo'lmaydi.",
        "msg_sent_success": "✅ Xabar foydalanuvchiga muvaffaqiyatli yuborildi.",
        "msg_sent_error": "❌ Xabarni foydalanuvchiga yuborib bo'lmaydi.",
        "cancelled": "Operatsiya bekor qilindi.",
        "pending_empty": "🎉 Barcha anketalar ko'rib chiqildi! Javob berilmaganlar yo'q.",
        "pending_title": "📋 <b>Javob berilmagan anketalar ro'yxati ({count}):</b>",
        "app_card_title": "📥 <b>JAVOB BERILMAGAN ANKETA №{app_id}</b>"
    },
    "en": {
        "welcome": (
            "Hello! This is the <b>EYUF</b> bot.\n\n"
            "Select language / Выберите язык / Tilni tanlang:"
        ),
        "lang_selected": (
            "English language selected 🇬🇧\n\n"
            "Click the button below to fill out the application."
        ),
        "btn_fill": "📝 Fill out application",
        "btn_change_lang": "🌐 Change language",
        "btn_pending": "📋 Pending applications",
        "fill_instructions": (
            "Copy the template below (tap on it to copy), "
            "fill in all fields after the colon, and send as a <b>single message</b>:\n\n"
            "{template}\n\n"
            "Example of a filled line:\n"
            "<code>Full Name: John Michael Smith</code>"
        ),
        "not_text": "Please send the application as text using the template above.",
        "missing_fields": (
            "❗ Not all fields are filled. Missing:\n\n"
            "{missing_text}\n\n"
            "Copy the template again, fill in all fields after the colon, and send as a single message:\n\n"
            "{template}"
        ),
        "prompt_university": "🏛️ Great! Now enter the <b>University name</b>:",
        "prompt_offer_letter": "📄 Please send your <b>Offer Letter</b> (as a document/file):",
        "not_a_document": "⚠️ Please send the Offer Letter as a file/document.",
        "app_submitted": (
            "✅ <b>Application successfully submitted!</b>\n\n"
            "Please wait for an administrator's response. "
            "You will be able to send messages after the admin replies to you."
        ),
        "wait_for_admin": "⏳ Your application is under review. Please wait for an administrator's response.",
        "doc_received_caption": (
            "📄 <b>Your document</b>\n\n"
            "The document was sent by the administrator."
        ),
        "msg_received_prefix": "💬 <b>Message from administrator:</b>\n\n",
        "btn_send_file": "📄 Send file",
        "btn_send_msg": "💬 Send message",
        "admin_prompt_file": (
            "📎 Now send the <b>file</b> here.\n\n"
            "Recipient: <b>{name}</b>\n"
            "Telegram ID: <code>{tg_id}</code>\n\n"
            "To cancel: /cancel"
        ),
        "admin_prompt_msg": (
            "💬 Enter a <b>text message</b> for the user.\n\n"
            "Recipient: <b>{name}</b>\n"
            "Telegram ID: <code>{tg_id}</code>\n\n"
            "To cancel: /cancel"
        ),
        "file_sent_success": "✅ File successfully sent to the user.",
        "file_sent_error": "❌ Failed to send file to the user.",
        "msg_sent_success": "✅ Message successfully sent to the user.",
        "msg_sent_error": "❌ Failed to send message to the user.",
        "cancelled": "Operation cancelled.",
        "pending_empty": "🎉 All applications have been processed! No pending ones.",
        "pending_title": "📋 <b>List of pending applications ({count}):</b>",
        "app_card_title": "📥 <b>PENDING APPLICATION №{app_id}</b>"
    }
}

FILL_BTNS = [LOCALES[l]["btn_fill"] for l in LOCALES]
LANG_BTNS = [LOCALES[l]["btn_change_lang"] for l in LOCALES]
PENDING_BTNS = [LOCALES[l]["btn_pending"] for l in LOCALES]

# ============================================================
# 1. НАСТРОЙКИ И ИНИЦИАЛИЗАЦИЯ
# ============================================================

BOT_TOKEN = "8946151948:AAG_RhZv-UOpHp5xi7vF5MN35GyCP-QIaj8"

ADMIN_IDS = {
    5039871861,
7678209331,
}

DATABASE = "applications.db"

logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# ============================================================
# 2. СОСТОЯНИЯ
# ============================================================

class ApplicationForm(StatesGroup):
    waiting_for_submission = State()
    waiting_for_university = State()
    waiting_for_offer_letter = State()
    waiting_for_admin_reply = State()


class AdminStates(StatesGroup):
    waiting_for_file = State()
    waiting_for_message = State()

# ============================================================
# 3. DATABASE
# ============================================================

async def init_db():
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                telegram_id INTEGER PRIMARY KEY,
                language TEXT DEFAULT 'ru'
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS applications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                telegram_id INTEGER NOT NULL,
                username TEXT,
                full_name TEXT NOT NULL,
                passport TEXT NOT NULL,
                student_id TEXT NOT NULL,
                date_of_birth TEXT NOT NULL,
                university TEXT NOT NULL,
                program_major TEXT NOT NULL,
                start_date TEXT NOT NULL,
                end_date TEXT NOT NULL,
                mode_of_study TEXT NOT NULL,
                offer_file_id TEXT,
                status TEXT DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        try:
            await db.execute("ALTER TABLE applications ADD COLUMN offer_file_id TEXT")
        except Exception:
            pass
        await db.commit()


async def set_user_language(telegram_id: int, lang: str):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("""
            INSERT INTO users (telegram_id, language)
            VALUES (?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET language=excluded.language
        """, (telegram_id, lang))
        await db.commit()


async def get_user_language(telegram_id: int) -> str:
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("SELECT language FROM users WHERE telegram_id = ?", (telegram_id,))
        row = await cursor.fetchone()
        return row[0] if row else "ru"


async def save_application(user_id, username, data):
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("""
            INSERT INTO applications (
                telegram_id, username, full_name, passport, student_id,
                date_of_birth, university, program_major, start_date,
                end_date, mode_of_study, offer_file_id, status
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
        """, (
            user_id, username, data["full_name"], data["passport"],
            data["student_id"], data["date_of_birth"], data["university"],
            data["program_major"], data["start_date"], data["end_date"],
            data["mode_of_study"], data.get("offer_file_id")
        ))
        await db.commit()
        return cursor.lastrowid


async def mark_application_answered(application_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        await db.execute("UPDATE applications SET status = 'answered' WHERE id = ?", (application_id,))
        await db.commit()


async def get_pending_applications():
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("""
            SELECT id, telegram_id, username, full_name, passport, student_id,
                   date_of_birth, university, program_major, start_date,
                   end_date, mode_of_study, offer_file_id, created_at
            FROM applications
            WHERE status = 'pending'
            ORDER BY id DESC
        """)
        return await cursor.fetchall()


async def get_application(application_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("""
            SELECT telegram_id, full_name
            FROM applications
            WHERE id = ?
        """, (application_id,))
        return await cursor.fetchone()


async def get_latest_application_by_user(telegram_id: int):
    async with aiosqlite.connect(DATABASE) as db:
        cursor = await db.execute("""
            SELECT id, full_name FROM applications 
            WHERE telegram_id = ? 
            ORDER BY id DESC LIMIT 1
        """, (telegram_id,))
        return await cursor.fetchone()

# ============================================================
# 4. ШАБЛОН И ПАРСИНГ
# ============================================================

FIELD_ORDER = [
    "full_name", "passport", "student_id", "date_of_birth",
    "program_major", "start_date", "end_date", "mode_of_study"
]

FIELD_LABELS = {
    "full_name": "Full Name",
    "passport": "Passport",
    "student_id": "Student ID",
    "date_of_birth": "Date of birth",
    "program_major": "Program and Major",
    "start_date": "Start date",
    "end_date": "End date",
    "mode_of_study": "Mode of study",
}

LABEL_TO_FIELD = {label.strip().lower(): field for field, label in FIELD_LABELS.items()}


def application_template() -> str:
    lines = "\n".join(f"{FIELD_LABELS[f]}: " for f in FIELD_ORDER)
    return f"<pre>{lines}</pre>"


def parse_application(text: str):
    data = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        label, _, value = line.partition(":")
        label_norm = label.strip().lower()
        value = value.strip()

        field = LABEL_TO_FIELD.get(label_norm)
        if field and value:
            data[field] = value

    missing = [f for f in FIELD_ORDER if f not in data]
    return data, missing

# ============================================================
# 5. КНОПКИ
# ============================================================

def lang_choice_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="set_lang:ru"),
                InlineKeyboardButton(text="🇺🇿 O'zbekcha", callback_data="set_lang:uz"),
                InlineKeyboardButton(text="🇬🇧 English", callback_data="set_lang:en"),
            ]
        ]
    )


def main_keyboard(lang: str = "ru", is_admin: bool = False):
    texts = LOCALES.get(lang, LOCALES["ru"])
    keyboard_buttons = []
    
    if is_admin:
        keyboard_buttons.append([KeyboardButton(text=texts["btn_pending"])])
        
    keyboard_buttons.append([KeyboardButton(text=texts["btn_fill"])])
    keyboard_buttons.append([KeyboardButton(text=texts["btn_change_lang"])])

    return ReplyKeyboardMarkup(
        keyboard=keyboard_buttons,
        resize_keyboard=True
    )


def admin_keyboard(application_id: int, lang: str = "ru"):
    texts = LOCALES.get(lang, LOCALES["ru"])
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=texts["btn_send_file"], callback_data=f"sendfile:{application_id}"),
                InlineKeyboardButton(text=texts["btn_send_msg"], callback_data=f"sendmsg:{application_id}")
            ]
        ]
    )

answered_keyboard = InlineKeyboardMarkup(
    inline_keyboard=[[InlineKeyboardButton(text="✅ Отвечено", callback_data="already_answered")]]
)

# ============================================================
# 6. КОМАНДЫ (START, LANG, PENDING, SEND)
# ============================================================

@dp.message(Command("start"))
async def start(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_user_language(message.from_user.id)
    texts = LOCALES[lang]

    await message.answer(
        texts["welcome"],
        reply_markup=lang_choice_keyboard(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data.startswith("set_lang:"))
async def process_language_choice(callback: CallbackQuery):
    lang = callback.data.split(":")[1]
    if lang not in LOCALES:
        lang = "ru"

    await set_user_language(callback.from_user.id, lang)
    texts = LOCALES[lang]

    is_admin = callback.from_user.id in ADMIN_IDS

    try:
        await callback.message.delete()
    except Exception:
        pass

    await callback.message.answer(
        texts["lang_selected"],
        parse_mode="HTML",
        reply_markup=main_keyboard(lang, is_admin=is_admin)
    )
    await callback.answer()


@dp.message(F.text.in_(LANG_BTNS))
async def change_language(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_user_language(message.from_user.id)
    texts = LOCALES[lang]

    await message.answer(
        texts["welcome"],
        reply_markup=lang_choice_keyboard(),
        parse_mode="HTML"
    )


@dp.message(Command("pending"))
@dp.message(F.text.in_(PENDING_BTNS))
async def show_pending_applications(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    admin_lang = await get_user_language(message.from_user.id)
    texts = LOCALES[admin_lang]

    pending = await get_pending_applications()
    if not pending:
        await message.answer(texts["pending_empty"])
        return

    await message.answer(texts["pending_title"].format(count=len(pending)), parse_mode="HTML")
    
    for row in pending:
        (app_id, tg_id, username, full_name, passport, student_id,
         date_of_birth, university, program_major, start_date,
         end_date, mode_of_study, offer_file_id, created_at) = row

        username_text = f"@{username}" if username else "нет/no"
        card_title = texts["app_card_title"].format(app_id=app_id)

        msg = (
            f"{card_title}\n\n"
            f"🆔 Application ID: <code>{app_id}</code>\n"
            f"👤 Telegram ID: <code>{tg_id}</code>\n"
            f"🔗 Username: {username_text}\n"
            f"📅 Date: {created_at}\n\n"
            f"<b>Full Name:</b> {full_name}\n"
            f"<b>Passport:</b> {passport}\n"
            f"<b>Student ID:</b> {student_id}\n"
            f"<b>Date of birth:</b> {date_of_birth}\n"
            f"<b>University:</b> {university}\n"
            f"<b>Program and Major:</b> {program_major}\n"
            f"<b>Start date:</b> {start_date}\n"
            f"<b>End date:</b> {end_date}\n"
            f"<b>Mode of study:</b> {mode_of_study}"
        )

        if offer_file_id:
            await message.answer_document(
                document=offer_file_id,
                caption=msg,
                parse_mode="HTML",
                reply_markup=admin_keyboard(app_id, lang=admin_lang)
            )
        else:
            await message.answer(msg, parse_mode="HTML", reply_markup=admin_keyboard(app_id, lang=admin_lang))


@dp.message(Command("send"))
async def cmd_send_direct(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return

    args = message.text.split(maxsplit=2)
    if len(args) < 3:
        await message.answer("⚠️ Использование: <code>/send &lt;ID&gt; &lt;текст&gt;</code>", parse_mode="HTML")
        return

    target_id_str = args[1]
    text_to_send = args[2]

    try:
        target_id = int(target_id_str)
    except ValueError:
        await message.answer("❌ ID должен быть числом.")
        return

    target_user_id = target_id
    app = await get_application(target_id)
    if app:
        target_user_id = app[0]
        await mark_application_answered(target_id)

    user_lang = await get_user_language(target_user_id)
    prefix = LOCALES[user_lang]["msg_received_prefix"]

    try:
        await bot.send_message(chat_id=target_user_id, text=f"{prefix}{text_to_send}", parse_mode="HTML")
        await message.answer(f"✅ Сообщение отправлено пользователю <code>{target_user_id}</code>.", parse_mode="HTML")
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}", parse_mode="HTML")

# ============================================================
# 7. АНКЕТИРОВАНИЕ (ПОШАГОВОЕ С УНИВЕРСИТЕТОМ И OFFER LETTER)
# ============================================================

@dp.message(F.text.in_(FILL_BTNS))
async def start_application(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(ApplicationForm.waiting_for_submission)

    lang = await get_user_language(message.from_user.id)
    texts = LOCALES[lang]

    await message.answer(
        texts["fill_instructions"].format(template=application_template()),
        parse_mode="HTML"
    )


@dp.message(ApplicationForm.waiting_for_submission)
async def process_application_text(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    texts = LOCALES[lang]

    if not message.text:
        await message.answer(texts["not_text"])
        return

    data, missing = parse_application(message.text)

    if missing:
        missing_text = "\n".join(f"• {FIELD_LABELS[f]}" for f in missing)
        await message.answer(
            texts["missing_fields"].format(missing_text=missing_text, template=application_template()),
            parse_mode="HTML"
        )
        return

    await state.update_data(app_data=data)
    await state.set_state(ApplicationForm.waiting_for_university)
    await message.answer(texts["prompt_university"], parse_mode="HTML")


@dp.message(ApplicationForm.waiting_for_university)
async def process_university(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    texts = LOCALES[lang]

    if not message.text:
        await message.answer("Пожалуйста, введите название университета текстом.")
        return

    user_data = await state.get_data()
    app_data = user_data.get("app_data", {})
    app_data["university"] = message.text.strip()

    await state.update_data(app_data=app_data)
    await state.set_state(ApplicationForm.waiting_for_offer_letter)
    await message.answer(texts["prompt_offer_letter"], parse_mode="HTML")


@dp.message(ApplicationForm.waiting_for_offer_letter)
async def process_offer_letter(message: Message, state: FSMContext):
    lang = await get_user_language(message.from_user.id)
    texts = LOCALES[lang]

    if not message.document:
        await message.answer(texts["not_a_document"])
        return

    user_data = await state.get_data()
    app_data = user_data.get("app_data", {})
    app_data["offer_file_id"] = message.document.file_id

    user_id = message.from_user.id
    username = message.from_user.username

    application_id = await save_application(user_id, username, app_data)
    await message.answer(texts["app_submitted"], parse_mode="HTML")

    await state.set_state(ApplicationForm.waiting_for_admin_reply)

    username_text = f"@{username}" if username else "нет username"

    admin_text = (
        "📥 <b>НОВАЯ АНКЕТА</b>\n\n"
        f"🆔 Application ID: <code>{application_id}</code>\n"
        f"👤 Telegram ID: <code>{user_id}</code>\n"
        f"🌐 Язык: <b>{lang.upper()}</b>\n"
        f"🔗 Username: {username_text}\n\n"
        f"<b>Full Name:</b> {app_data['full_name']}\n"
        f"<b>Passport:</b> {app_data['passport']}\n"
        f"<b>Student ID:</b> {app_data['student_id']}\n"
        f"<b>Date of birth:</b> {app_data['date_of_birth']}\n"
        f"<b>University:</b> {app_data['university']}\n"
        f"<b>Program and Major:</b> {app_data['program_major']}\n"
        f"<b>Start date:</b> {app_data['start_date']}\n"
        f"<b>End date:</b> {app_data['end_date']}\n"
        f"<b>Mode of study:</b> {app_data['mode_of_study']}"
    )

    for admin_id in ADMIN_IDS:
        try:
            admin_lang = await get_user_language(admin_id)
            await bot.send_document(
                chat_id=admin_id,
                document=message.document.file_id,
                caption=admin_text,
                parse_mode="HTML",
                reply_markup=admin_keyboard(application_id, lang=admin_lang)
            )
        except Exception as e:
            logging.error("Ошибка отправки админу %s: %s", admin_id, e)


@dp.message(ApplicationForm.waiting_for_admin_reply)
async def block_user_spam(message: Message):
    lang = await get_user_language(message.from_user.id)
    await message.answer(LOCALES[lang]["wait_for_admin"])

# ============================================================
# 8. ОБРАБОТКА ДЕЙСТВИЙ АДМИНА
# ============================================================

@dp.callback_query(F.data.startswith("sendfile:"))
async def admin_send_file_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет доступа / Access denied.", show_alert=True)
        return

    application_id = int(callback.data.split(":")[1])
    application = await get_application(application_id)

    if application is None:
        await callback.answer("Анкета не найдена / Application not found.", show_alert=True)
        return

    telegram_id, full_name = application

    await state.update_data(
        target_user_id=telegram_id,
        application_id=application_id,
        target_name=full_name,
        message_id=callback.message.message_id,
        chat_id=callback.message.chat.id
    )
    await state.set_state(AdminStates.waiting_for_file)

    admin_lang = await get_user_language(callback.from_user.id)
    texts = LOCALES[admin_lang]

    await callback.message.answer(
        texts["admin_prompt_file"].format(name=full_name, tg_id=telegram_id),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.callback_query(F.data.startswith("sendmsg:"))
async def admin_send_msg_callback(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("У вас нет доступа / Access denied.", show_alert=True)
        return

    application_id = int(callback.data.split(":")[1])
    application = await get_application(application_id)

    if application is None:
        await callback.answer("Анкета не найдена / Application not found.", show_alert=True)
        return

    telegram_id, full_name = application

    await state.update_data(
        target_user_id=telegram_id,
        application_id=application_id,
        target_name=full_name,
        message_id=callback.message.message_id,
        chat_id=callback.message.chat.id
    )
    await state.set_state(AdminStates.waiting_for_message)

    admin_lang = await get_user_language(callback.from_user.id)
    texts = LOCALES[admin_lang]

    await callback.message.answer(
        texts["admin_prompt_msg"].format(name=full_name, tg_id=telegram_id),
        parse_mode="HTML"
    )
    await callback.answer()


@dp.message(StateFilter(AdminStates.waiting_for_file), F.document)
async def receive_file(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    target_user_id = data["target_user_id"]
    application_id = data.get("application_id")

    user_lang = await get_user_language(target_user_id)
    caption = LOCALES[user_lang]["doc_received_caption"]

    admin_lang = await get_user_language(message.from_user.id)
    admin_texts = LOCALES[admin_lang]

    try:
        await bot.send_document(
            chat_id=target_user_id,
            document=message.document.file_id,
            caption=caption,
            parse_mode="HTML"
        )
        if application_id:
            await mark_application_answered(application_id)

        user_state = dp.fsm.get_context(bot=bot, chat_id=target_user_id, user_id=target_user_id)
        await user_state.clear()

        if "message_id" in data and "chat_id" in data:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=data["chat_id"],
                    message_id=data["message_id"],
                    reply_markup=answered_keyboard
                )
            except Exception as e:
                logging.error("Не удалось обновить кнопки: %s", e)

        await message.answer(admin_texts["file_sent_success"])
    except Exception as e:
        logging.error("Ошибка отправки файла: %s", e)
        await message.answer(admin_texts["file_sent_error"])

    await state.clear()


@dp.message(StateFilter(AdminStates.waiting_for_message), F.text)
async def receive_message_for_user(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return

    data = await state.get_data()
    target_user_id = data["target_user_id"]
    application_id = data.get("application_id")

    user_lang = await get_user_language(target_user_id)
    prefix = LOCALES[user_lang]["msg_received_prefix"]

    admin_lang = await get_user_language(message.from_user.id)
    admin_texts = LOCALES[admin_lang]

    try:
        await bot.send_message(
            chat_id=target_user_id,
            text=f"{prefix}{message.text}",
            parse_mode="HTML"
        )
        if application_id:
            await mark_application_answered(application_id)

        user_state = dp.fsm.get_context(bot=bot, chat_id=target_user_id, user_id=target_user_id)
        await user_state.clear()

        if "message_id" in data and "chat_id" in data:
            try:
                await bot.edit_message_reply_markup(
                    chat_id=data["chat_id"],
                    message_id=data["message_id"],
                    reply_markup=answered_keyboard
                )
            except Exception as e:
                logging.error("Не удалось обновить кнопки: %s", e)

        await message.answer(admin_texts["msg_sent_success"])
    except Exception as e:
        logging.error("Ошибка отправки сообщения: %s", e)
        await message.answer(admin_texts["msg_sent_error"])

    await state.clear()


@dp.callback_query(F.data == "already_answered")
async def already_answered_handler(callback: CallbackQuery):
    await callback.answer("Ответ уже отправлен / Already answered.", show_alert=True)


@dp.message(Command("cancel"))
async def cancel(message: Message, state: FSMContext):
    await state.clear()
    lang = await get_user_language(message.from_user.id)
    await message.answer(LOCALES[lang]["cancelled"])

# ============================================================
# 9. ДВУСТОРОННИЙ ЧАТ
# ============================================================

@dp.message(F.chat.type == "private", StateFilter(None))
async def user_chat_forwarder(message: Message, state: FSMContext):
    if message.from_user.id in ADMIN_IDS:
        return

    app = await get_latest_application_by_user(message.from_user.id)
    if not app:
        return

    app_id, full_name = app

    for admin_id in ADMIN_IDS:
        try:
            admin_lang = await get_user_language(admin_id)
            msg_header = (
                f"📩 <b>Новое сообщение от пользователя!</b>\n"
                f"👤 Имя: {full_name}\n"
                f"🆔 Application ID: <code>{app_id}</code>\n"
                f"Telegram ID: <code>{message.from_user.id}</code>\n"
                f"----------------------------"
            )
            await bot.send_message(chat_id=admin_id, text=msg_header, parse_mode="HTML")
            await message.copy_to(chat_id=admin_id, reply_markup=admin_keyboard(app_id, lang=admin_lang))
        except Exception as e:
            logging.error("Ошибка при пересылке админу: %s", e)

# ============================================================
# 10. MAIN
# ============================================================

class HealthHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"EYUF Telegram bot is running.")

    def do_HEAD(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()

    def log_message(self, format, *args):
        # Keep Render logs focused on the Telegram bot.
        return


def start_health_server():
    port = int(os.environ.get("PORT", "10000"))
    server = ThreadingHTTPServer(("0.0.0.0", port), HealthHandler)
    logging.info("Health server listening on port %s", port)
    server.serve_forever()


async def main():
    await init_db()

    # Render Web Services require an open HTTP port.
    # The Telegram bot still uses polling in the main thread.
    threading.Thread(target=start_health_server, daemon=True).start()

    print("======================================")
    print("BOT STARTED SUCCESSFULLY")
    print("======================================")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
# -*- coding: utf-8 -*-
import asyncio, base64, logging, os, sqlite3, tempfile
from io import BytesIO
import httpx
from dotenv import load_dotenv
from openai import OpenAI
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton, LabeledPrice, PreCheckoutQuery,
)
from aiogram.types.input_file import BufferedInputFile

load_dotenv()
BOT_TOKEN         = os.getenv('BOT_TOKEN', '').strip()
OPENAI_API_KEY    = os.getenv('OPENAI_API_KEY', '').strip()
REPLICATE_API_KEY = os.getenv('REPLICATE_API_KEY', '').strip()
COST_IMAGE_GEN    = int(os.getenv('COST_IMAGE_GEN', '5'))
COST_IMAGE_EDIT   = int(os.getenv('COST_IMAGE_EDIT', '5'))
COST_VIDEO        = int(os.getenv('COST_VIDEO', '30'))
IMAGE_MODEL       = os.getenv('IMAGE_MODEL', 'gpt-image-1').strip()
IMAGE_SIZE        = os.getenv('IMAGE_SIZE', '1024x1024').strip()
VIDEO_ENABLED     = os.getenv('VIDEO_ENABLED', '0').strip() == '1'
if not BOT_TOKEN: raise RuntimeError('BOT_TOKEN is empty')
if not OPENAI_API_KEY: raise RuntimeError('OPENAI_API_KEY is empty')

T = {
    "ru": {
        "welcome": "🤖 Привет! Я — AI-бот для создания изображений и видео.\n\n🎨 Что я умею:\n• Генерировать изображение по описанию\n• Редактировать твоё фото (фон, объекты, стиль)\n• Дорабатывать последнюю картинку ещё раз\n• Создавать короткое видео (5 сек, 1080p)\n\n💰 Цены:\n• 🎨 1 рисунок = 5 кредитов\n• 🖼 1 редактирование = 5 кредитов\n• 🎬 1 видео = 30 кредитов\n\n⭐ Пакеты звёзд:\n• 50 ⭐ → 10 кр. (2 рисунка)\n• 100 ⭐ → 20 кр. (4 рисунка)\n• 150 ⭐ → 30 кр. (1 видео)\n\n💳 Купить звёзды: @litencyy",
        "choose_lang": "Выбери язык / Tilni tanlang:",
        "menu": "✅ Меню открыто.",
        "balance": "💳 Баланс: {credits} кредит(ов).",
        "not_enough": "⚠️ Недостаточно кредитов!\n💳 Баланс: {have} кр., нужно: {need} кр.\n\n💰 Пакеты:\n• 50 ⭐ → 10 кр.\n• 100 ⭐ → 20 кр.\n• 150 ⭐ → 30 кр.\n\n⭐ Пополни у @litencyy ↓",
        "buy": "⭐ Купить кредиты",
        "help": "ℹ️ Как пользоваться:\n\n🎨 Генерация — опиши что создать (5 кр.)\n  Пример: красивый закат над горами\n\n🖼 Редактирование — фото + что изменить (5 кр.)\n  Пример: сделай фон космосом\n\n🔄 Повторная правка — доработать последнюю картинку (5 кр.)\n\n🎬 Видео — опиши сцену, получи 5-сек видео 1080p (30 кр.)\n\n⭐ Купить звёзды: @litencyy",
        "info": "📊 О боте:\n\n🤖 Название: FotoRestavr Bot\n🔧 Технология: GPT-Image-1 + Kling AI\n🌐 Языки: Русский, Узбекский\n\n🎨 Цены:\n• Генерация — 5 кр.\n• Редактирование — 5 кр.\n• Видео (1080p, 5 сек) — 30 кр.\n\n⭐ Пакеты:\n• 50 ⭐ → 10 кр. | 100 ⭐ → 20 кр. | 150 ⭐ → 30 кр.\n\n💳 Пополнить: @litencyy",
        "ask_gen": "✍️ Напиши, что сгенерировать.",
        "ask_edit_photo": "📸 Отправь фото для редактирования.",
        "ask_edit_prompt": "✍️ Напиши, что изменить на фото.",
        "ask_reedit_prompt": "✍️ Напиши, что ещё изменить.",
        "ask_video": "✍️ Опиши видео (5 сек, 1080p).",
        "processing": "⏳ Делаю... это займёт 1-3 минуты.",
        "done": "✅ Готово.",
        "cancelled": "❌ Отменено.",
        "no_last_image": "⚠️ Нет последней картинки.",
        "video_disabled": "🎬 Видео не подключено.",
        "billing_limit": "⚠️ Ошибка OpenAI: лимит биллинга.",
        "choose_pack": "Выбери пакет:",
        "pay_title": "Пакет кредитов",
        "pay_desc": "Пополнение баланса бота.",
        "paid_ok": "✅ Оплачено! +{add} кредитов. Баланс: {credits}.",
        "unknown_text": "⭐ Пополни звёзды у @litencyy или выбери действие в меню.",
        "lang_set": "🌐 Язык: Русский",
    },
    "uz": {
        "welcome": "🤖 Salom! Men — rasm va video yaratuvchi AI-bot.\n\n🎨 Nima qila olaman:\n• Tavsif bo'yicha rasm yaratish\n• Fotoni tahrirlash (fon, obyektlar, uslub)\n• Oxirgi rasmni qayta tahrirlash\n• Qisqa video yaratish (5 soniya, 1080p)\n\n💰 Narxlar:\n• 🎨 1 rasm = 5 kredit\n• 🖼 1 tahrirlash = 5 kredit\n• 🎬 1 video = 30 kredit\n\n⭐ Kredit paketlari:\n• 50 ⭐ → 10 kr. (2 ta rasm)\n• 100 ⭐ → 20 kr. (4 ta rasm)\n• 150 ⭐ → 30 kr. (1 ta video)\n\n💳 Yulduz sotib olish: @litencyy",
        "choose_lang": "Tilni tanlang / Выбери язык:",
        "menu": "✅ Menyu ochildi.",
        "balance": "💳 Balans: {credits} kredit.",
        "not_enough": "⚠️ Kredit yetarli emas!\n💳 Balans: {have} kr., kerak: {need} kr.\n\n💰 Paketlar:\n• 50 ⭐ → 10 kr.\n• 100 ⭐ → 20 kr.\n• 150 ⭐ → 30 kr.\n\n⭐ @litencyy dan sotib oling ↓",
        "buy": "⭐ Kredit sotib olish",
        "help": "ℹ️ Qanday ishlaydi:\n\n🎨 Generatsiya — nima yaratishni yozing (5 kr.)\n  Misol: tog'lar ustida chiroyli quyosh\n\n🖼 Tahrirlash — foto + nima o'zgartirishni yozing (5 kr.)\n  Misol: fonni kosmosga o'zgartir\n\n🔄 Qayta tahrir — oxirgi rasmni qayta ishlash (5 kr.)\n\n🎬 Video — sahnani tasvirla, 5 soniya 1080p (30 kr.)\n\n⭐ Yulduz sotib olish: @litencyy",
        "info": "📊 Bot haqida:\n\n🤖 Nomi: FotoRestavr Bot\n🔧 Texnologiya: GPT-Image-1 + Kling AI\n🌐 Tillar: Ruscha, O'zbekcha\n\n🎨 Narxlar:\n• Rasm yaratish — 5 kr.\n• Tahrirlash — 5 kr.\n• Video (1080p, 5 soniya) — 30 kr.\n\n⭐ Paketlar:\n• 50 ⭐ → 10 kr. | 100 ⭐ → 20 kr. | 150 ⭐ → 30 kr.\n\n💳 To'ldirish: @litencyy",
        "ask_gen": "✍️ Nima yaratishni yozing.",
        "ask_edit_photo": "📸 Tahrirlanadigan fotoni yuboring.",
        "ask_edit_prompt": "✍️ Nima o'zgartirishni yozing.",
        "ask_reedit_prompt": "✍️ Yana nima o'zgartiramiz?",
        "ask_video": "✍️ Video uchun matn yozing (5 soniya, 1080p).",
        "processing": "⏳ Tayyorlayapman... 1-3 daqiqa ketishi mumkin.",
        "done": "✅ Tayyor.",
        "cancelled": "❌ Bekor qilindi.",
        "no_last_image": "⚠️ Oxirgi rasm yo'q.",
        "video_disabled": "🎬 Video hozircha ulanmagan.",
        "billing_limit": "⚠️ OpenAI xatolik: billing limiti tugagan.",
        "choose_pack": "Kredit paketini tanlang:",
        "pay_title": "Kredit paketi",
        "pay_desc": "Bot balansini to'ldirish.",
        "paid_ok": "✅ To'lov o'tdi! +{add} kredit. Balans: {credits}.",
        "unknown_text": "⭐ Yulduzlarni @litencyy dan sotib oling yoki menyudan tanlang.",
        "lang_set": "🌐 Til: O'zbekcha",
    },
}

BTN = {
    "ru": {
        "gen": "🎨 Генерация",
        "edit": "🖼 Редактирование",
        "reedit": "🔄 Повторная правка",
        "video": "🎬 Видео",
        "bal": "💳 Баланс",
        "help": "ℹ️ Помощь",
        "lang": "🌐 Язык",
        "cancel": "❌ Отмена",
    },
    "uz": {
        "gen": "🎨 Generatsiya",
        "edit": "🖼 Tahrirlash",
        "reedit": "🔄 Qayta tahrir",
        "video": "🎬 Video",
        "bal": "💳 Balans",
        "help": "ℹ️ Yordam",
        "lang": "🌐 Til",
        "cancel": "❌ Bekor qilish",
    },
}


def tr(lang, key, **kwargs):
    lang = lang if lang in T else "ru"
    return T[lang].get(key, key).format(**kwargs)

def menu_kb(lang):
    b = BTN[lang]
    return ReplyKeyboardMarkup(keyboard=[
        [KeyboardButton(text=b["gen"]),    KeyboardButton(text=b["edit"])],
        [KeyboardButton(text=b["reedit"]), KeyboardButton(text=b["video"])],
        [KeyboardButton(text=b["bal"]),    KeyboardButton(text=b["help"])],
        [KeyboardButton(text=b["lang"]),   KeyboardButton(text=b["cancel"])],
    ], resize_keyboard=True)

def lang_kb():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Русский 🇷🇺", callback_data="lang:ru"),
        InlineKeyboardButton(text="O'zbek 🇺🇿",  callback_data="lang:uz"),
    ]])

def buy_kb(lang):
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=tr(lang, "buy"), callback_data="buy:menu")
    ]])

def packs():
    return [("pack10", 10, 50), ("pack20", 20, 100), ("pack30", 30, 150)]

def packs_kb(lang):
    ru = lang == "ru"
    rows = []
    for pid, cr, stars in packs():
        label = f"⭐ {stars} Stars → +{cr} кредитов" if ru else f"⭐ {stars} Stars → +{cr} kredit"
        rows.append([InlineKeyboardButton(text=label, callback_data=f"buy:{pid}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

DB_PATH = "bot.db"
conn = sqlite3.connect(DB_PATH)
conn.execute(
    "CREATE TABLE IF NOT EXISTS users ("
    "user_id INTEGER PRIMARY KEY,"
    "lang TEXT DEFAULT 'ru',"
    "credits INTEGER DEFAULT 0,"
    "last_image_file_id TEXT DEFAULT NULL,"
    "tmp_image_file_id TEXT DEFAULT NULL,"
    "created_at INTEGER DEFAULT (strftime('%s','now')))"
)
conn.commit()

def db_get_user(uid):
    row = conn.execute(
        "SELECT user_id,lang,credits,last_image_file_id,tmp_image_file_id FROM users WHERE user_id=?",
        (uid,)
    ).fetchone()
    if not row:
        conn.execute("INSERT INTO users(user_id,lang,credits) VALUES(?,?,?)", (uid,"ru",0))
        conn.commit()
        return {"user_id":uid,"lang":"ru","credits":0,"last_image_file_id":None,"tmp_image_file_id":None}
    return {"user_id":row[0],"lang":row[1],"credits":row[2],"last_image_file_id":row[3],"tmp_image_file_id":row[4]}

def db_set_lang(uid, lang):
    conn.execute("UPDATE users SET lang=? WHERE user_id=?", (lang,uid)); conn.commit()
def db_add_credits(uid, add):
    conn.execute("UPDATE users SET credits=credits+? WHERE user_id=?", (add,uid)); conn.commit()
    return db_get_user(uid)["credits"]
def db_take_credits(uid, take):
    conn.execute("UPDATE users SET credits=MAX(credits-?,0) WHERE user_id=?", (take,uid)); conn.commit()
def db_set_last_image(uid, fid):
    conn.execute("UPDATE users SET last_image_file_id=? WHERE user_id=?", (fid,uid)); conn.commit()
def db_set_tmp_image(uid, fid):
    conn.execute("UPDATE users SET tmp_image_file_id=? WHERE user_id=?", (fid,uid)); conn.commit()

class S(StatesGroup):
    GEN_PROMPT      = State()
    EDIT_WAIT_PHOTO = State()
    EDIT_PROMPT     = State()
    REEDIT_PROMPT   = State()
    VIDEO_PROMPT    = State()

client = OpenAI(api_key=OPENAI_API_KEY)
user_locks: dict = {}

def get_lock(uid):
    if uid not in user_locks:
        user_locks[uid] = asyncio.Lock()
    return user_locks[uid]

async def tg_file_bytes(bot, file_id):
    f = await bot.get_file(file_id)
    buf = BytesIO()
    await bot.download_file(f.file_path, buf)
    return buf.getvalue()

def _tmp(data, ext=".png"):
    fd, path = tempfile.mkstemp(suffix=ext)
    os.close(fd)
    open(path,"wb").write(data)
    return path

async def openai_gen_image(prompt):
    res = await asyncio.to_thread(client.images.generate, model=IMAGE_MODEL, prompt=prompt, size=IMAGE_SIZE)
    return base64.b64decode(res.data[0].b64_json)

async def openai_edit_image(img_bytes, prompt):
    path = _tmp(img_bytes)
    try:
        with open(path,"rb") as img:
            res = await asyncio.to_thread(client.images.edit, model=IMAGE_MODEL, image=img, prompt=prompt, size=IMAGE_SIZE)
        return base64.b64decode(res.data[0].b64_json)
    finally:
        try: os.remove(path)
        except: pass

async def replicate_gen_video(prompt):
    hdrs = {"Authorization": f"Bearer {REPLICATE_API_KEY}", "Content-Type": "application/json"}
    async with httpx.AsyncClient(timeout=300.0) as h:
        r = await h.post(
            "https://api.replicate.com/v1/models/klingai/kling-video/predictions",
            headers=hdrs,
            json={"input": {"prompt": prompt, "duration": 5, "aspect_ratio": "16:9"}},
        )
        r.raise_for_status()
        pred_id = r.json()["id"]
        for _ in range(150):
            rr = await h.get(f"https://api.replicate.com/v1/predictions/{pred_id}",
                             headers={"Authorization": f"Bearer {REPLICATE_API_KEY}"})
            rr.raise_for_status()
            d = rr.json()
            if d.get("status") == "succeeded":
                url = d["output"]
                if isinstance(url, list): url = url[0]
                rc = await h.get(url); rc.raise_for_status()
                return rc.content
            if d.get("status") == "failed":
                raise RuntimeError(f"Video failed: {d.get('error','?')}")
            await asyncio.sleep(3.0)
    raise RuntimeError("Video timeout")

async def has_credits(uid, need):
    u = db_get_user(uid)
    return u["credits"] >= need, u["credits"]

def is_cancel(t):
    return bool(t) and t.strip() in (BTN["ru"]["cancel"], BTN["uz"]["cancel"])
def is_btn(key, t):
    return bool(t) and t.strip() in (BTN["ru"][key], BTN["uz"][key])

logging.basicConfig(level=logging.INFO)
bot = Bot(BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
r   = Router()
dp.include_router(r)

@r.message(CommandStart())
async def cmd_start(m: Message):
    u = db_get_user(m.from_user.id)
    await m.answer(tr(u["lang"], "welcome"))
    await m.answer(tr(u["lang"], "choose_lang"), reply_markup=lang_kb())
    await m.answer(tr(u["lang"], "menu"), reply_markup=menu_kb(u["lang"]))

@r.message(Command("info"))
async def cmd_info(m: Message):
    u = db_get_user(m.from_user.id)
    await m.answer(tr(u["lang"], "info"), reply_markup=packs_kb(u["lang"]))

@r.message(Command("menu"))
async def cmd_menu(m: Message):
    u = db_get_user(m.from_user.id)
    await m.answer(tr(u["lang"], "menu"), reply_markup=menu_kb(u["lang"]))

@r.message(Command("balance"))
async def cmd_balance(m: Message):
    u = db_get_user(m.from_user.id)
    await m.answer(tr(u["lang"], "balance", credits=u["credits"]), reply_markup=buy_kb(u["lang"]))

@r.callback_query(F.data.startswith("lang:"))
async def cb_set_lang(cb: CallbackQuery):
    lang = cb.data.split(":")[1]
    if lang not in ("ru","uz"): lang = "ru"
    db_set_lang(cb.from_user.id, lang)
    try:
        await cb.answer()
    except Exception:
        pass
    await cb.message.answer(tr(lang, "lang_set"), reply_markup=menu_kb(lang))

@r.callback_query(F.data.startswith("buy:"))
async def cb_buy(cb: CallbackQuery):
    u = db_get_user(cb.from_user.id); lang = u["lang"]
    kind = cb.data.split(":",1)[1]
    try:
        await cb.answer()
    except Exception:
        pass
    if kind == "menu":
        await cb.message.answer(tr(lang,"choose_pack"), reply_markup=packs_kb(lang)); return
    sel = next(((p,c,s) for p,c,s in packs() if p==kind), None)
    if not sel:
        return
    pid, credits, stars = sel
    try:
        await bot.send_invoice(
            chat_id=cb.from_user.id,
            title=tr(lang,"pay_title"), description=tr(lang,"pay_desc"),
            payload=f"credits:{credits}", provider_token="", currency="XTR",
            prices=[LabeledPrice(label=f"+{credits} credits", amount=stars)],
        )
    except Exception as e:
        await cb.message.answer(f"Ошибка оплаты: {e}")

@r.pre_checkout_query()
async def pre_checkout(q: PreCheckoutQuery):
    await bot.answer_pre_checkout_query(q.id, ok=True)

@r.message(F.successful_payment)
async def on_payment(m: Message):
    u = db_get_user(m.from_user.id); lang = u["lang"]
    add = 0
    p = m.successful_payment.invoice_payload or ""
    if p.startswith("credits:"):
        try: add = int(p.split(":",1)[1])
        except: pass
    if add:
        cr = db_add_credits(m.from_user.id, add)
        await m.answer(tr(lang,"paid_ok", add=add, credits=cr), reply_markup=menu_kb(lang))
    else:
        await m.answer(tr(lang,"done"), reply_markup=menu_kb(lang))

@r.message(F.text)
async def on_text(m: Message, state: FSMContext):
    u = db_get_user(m.from_user.id); lang = u["lang"]; txt = m.text.strip()
    if is_cancel(txt):
        await state.clear(); db_set_tmp_image(m.from_user.id, None)
        await m.answer(tr(lang,"cancelled"), reply_markup=menu_kb(lang)); return
    if is_btn("lang", txt):
        await m.answer(tr(lang,"choose_lang"), reply_markup=lang_kb()); return
    if is_btn("help", txt):
        await m.answer(tr(lang,"help"), reply_markup=menu_kb(lang)); return
    if is_btn("bal", txt):
        u = db_get_user(m.from_user.id)
        await m.answer(tr(lang,"balance", credits=u["credits"]), reply_markup=packs_kb(lang)); return
    if is_btn("gen", txt):
        await state.set_state(S.GEN_PROMPT); await m.answer(tr(lang,"ask_gen")); return
    if is_btn("edit", txt):
        await state.set_state(S.EDIT_WAIT_PHOTO); await m.answer(tr(lang,"ask_edit_photo")); return
    if is_btn("reedit", txt):
        if not u["last_image_file_id"]:
            await m.answer(tr(lang,"no_last_image")); return
        await state.set_state(S.REEDIT_PROMPT); await m.answer(tr(lang,"ask_reedit_prompt")); return
    if is_btn("video", txt):
        await state.set_state(S.VIDEO_PROMPT); await m.answer(tr(lang,"ask_video")); return
    await m.answer(tr(lang,"unknown_text"), reply_markup=menu_kb(lang))

@r.message(S.GEN_PROMPT, F.text)
async def do_gen(m: Message, state: FSMContext):
    u = db_get_user(m.from_user.id); lang = u["lang"]
    ok, have = await has_credits(m.from_user.id, COST_IMAGE_GEN)
    if not ok:
        await m.answer(tr(lang,"not_enough", need=COST_IMAGE_GEN, have=have), reply_markup=packs_kb(lang)); return
    async with get_lock(m.from_user.id):
        await m.answer(tr(lang,"processing"))
        try:
            data = await openai_gen_image(m.text.strip())
        except Exception as e:
            s = str(e)
            await m.answer(tr(lang,"billing_limit") if "billing" in s.lower() else f"Error: {s}", reply_markup=menu_kb(lang)); return
        db_take_credits(m.from_user.id, COST_IMAGE_GEN)
        sent = await m.answer_photo(BufferedInputFile(data,"image.png"), caption=tr(lang,"done"), reply_markup=menu_kb(lang))
        try: db_set_last_image(m.from_user.id, sent.photo[-1].file_id)
        except: pass
    await state.clear()

@r.message(S.EDIT_WAIT_PHOTO, F.photo)
async def got_photo(m: Message, state: FSMContext):
    db_set_tmp_image(m.from_user.id, m.photo[-1].file_id)
    await state.set_state(S.EDIT_PROMPT)
    await m.answer(tr(db_get_user(m.from_user.id)["lang"],"ask_edit_prompt"))

@r.message(S.EDIT_WAIT_PHOTO)
async def wrong_photo(m: Message):
    await m.answer(tr(db_get_user(m.from_user.id)["lang"],"ask_edit_photo"))

@r.message(S.EDIT_PROMPT, F.text)
async def do_edit(m: Message, state: FSMContext):
    u = db_get_user(m.from_user.id); lang = u["lang"]
    if not u["tmp_image_file_id"]:
        await state.set_state(S.EDIT_WAIT_PHOTO); await m.answer(tr(lang,"ask_edit_photo")); return
    ok, have = await has_credits(m.from_user.id, COST_IMAGE_EDIT)
    if not ok:
        await m.answer(tr(lang,"not_enough", need=COST_IMAGE_EDIT, have=have), reply_markup=packs_kb(lang)); return
    async with get_lock(m.from_user.id):
        await m.answer(tr(lang,"processing"))
        try:
            raw = await tg_file_bytes(bot, u["tmp_image_file_id"])
            data = await openai_edit_image(raw, m.text.strip())
        except Exception as e:
            s = str(e)
            await m.answer(tr(lang,"billing_limit") if "billing" in s.lower() else f"Error: {s}", reply_markup=menu_kb(lang)); return
        db_take_credits(m.from_user.id, COST_IMAGE_EDIT)
        db_set_tmp_image(m.from_user.id, None)
        sent = await m.answer_photo(BufferedInputFile(data,"edit.png"), caption=tr(lang,"done"), reply_markup=menu_kb(lang))
        try: db_set_last_image(m.from_user.id, sent.photo[-1].file_id)
        except: pass
    await state.clear()

@r.message(S.REEDIT_PROMPT, F.text)
async def do_reedit(m: Message, state: FSMContext):
    u = db_get_user(m.from_user.id); lang = u["lang"]
    if not u["last_image_file_id"]:
        await m.answer(tr(lang,"no_last_image"), reply_markup=menu_kb(lang)); await state.clear(); return
    ok, have = await has_credits(m.from_user.id, COST_IMAGE_EDIT)
    if not ok:
        await m.answer(tr(lang,"not_enough", need=COST_IMAGE_EDIT, have=have), reply_markup=packs_kb(lang)); return
    async with get_lock(m.from_user.id):
        await m.answer(tr(lang,"processing"))
        try:
            raw = await tg_file_bytes(bot, u["last_image_file_id"])
            data = await openai_edit_image(raw, m.text.strip())
        except Exception as e:
            s = str(e)
            await m.answer(tr(lang,"billing_limit") if "billing" in s.lower() else f"Error: {s}", reply_markup=menu_kb(lang)); return
        db_take_credits(m.from_user.id, COST_IMAGE_EDIT)
        sent = await m.answer_photo(BufferedInputFile(data,"reedit.png"), caption=tr(lang,"done"), reply_markup=menu_kb(lang))
        try: db_set_last_image(m.from_user.id, sent.photo[-1].file_id)
        except: pass
    await state.clear()

@r.message(S.VIDEO_PROMPT, F.text)
async def do_video(m: Message, state: FSMContext):
    u = db_get_user(m.from_user.id); lang = u["lang"]
    if not VIDEO_ENABLED or not REPLICATE_API_KEY:
        await m.answer(tr(lang,"video_disabled"), reply_markup=menu_kb(lang)); await state.clear(); return
    ok, have = await has_credits(m.from_user.id, COST_VIDEO)
    if not ok:
        await m.answer(tr(lang,"not_enough", need=COST_VIDEO, have=have), reply_markup=packs_kb(lang)); return
    async with get_lock(m.from_user.id):
        await m.answer(tr(lang,"processing"))
        try:
            data = await replicate_gen_video(m.text.strip())
        except Exception as e:
            await m.answer(f"Error: {e}", reply_markup=menu_kb(lang)); return
        db_take_credits(m.from_user.id, COST_VIDEO)
        await m.answer_video(BufferedInputFile(data,"video.mp4"), caption=tr(lang,"done"), reply_markup=menu_kb(lang))
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

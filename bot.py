# -*- coding: utf-8 -*-
import asyncio
import json
import logging
import os
from typing import Dict, Any

from aiogram import Bot, Dispatcher, executor, types
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton,
    InlineKeyboardMarkup, InlineKeyboardButton
)

from config import TOKEN, ADMIN_ID, ADMIN_USERNAME, PDF_FILE

# ---------- ЛОГИ ----------
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
log = logging.getLogger("informat")

# ---------- ХРАНИЛИЩЕ СОСТОЯНИЙ (persist) ----------
STATE_FILE = "state.json"
_state: Dict[str, Any] = {"approved": [], "pending": []}

def load_state():
    global _state
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r", encoding="utf-8") as f:
                _state = json.load(f)
        except Exception:
            _state = {"approved": [], "pending": []}
    else:
        save_state()

def save_state():
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(_state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        log.warning("Can't save state: %s", e)

def set_pending(uid: int):
    if uid not in _state["pending"]:
        _state["pending"].append(uid)
        # если был approved — убираем
        if uid in _state["approved"]:
            _state["approved"].remove(uid)
    save_state()

def approve(uid: int):
    if uid not in _state["approved"]:
        _state["approved"].append(uid)
    if uid in _state["pending"]:
        _state["pending"].remove(uid)
    save_state()

def decline(uid: int):
    if uid in _state["pending"]:
        _state["pending"].remove(uid)
    if uid in _state["approved"]:
        _state["approved"].remove(uid)
    save_state()

def is_approved(uid: int) -> bool:
    return uid in _state["approved"]

def is_pending(uid: int) -> bool:
    return uid in _state["pending"]

# ---------- ТЕКСТЫ ----------
WELCOME = (
    "📥 <b>INFORMAT</b> Kursuna xoş gəlmisiniz!\n\n"
    "Qiymət: <b>199 AZN</b>\n\n"
    "💳 Ödəniş üçün üsul seçin:\n\n"
    "🔶 <b>(M10)</b>: +994502124244\n\n"
    "🟧 <b>Kripto (USDT TRC20)</b>: <code>TQGqAwprk8YBRsDUvJcBXA1mmBopZ3QFG</code>\n"
    "🟨 <b>Kripto (TON)</b>: <code>UQBayf08cTYayFobCa3B2XX3Q5SJp10_w13h7ELisevB5</code>\n\n"
    "📸 Ödəniş etdikdən sonra <b>check/screenshot</b> göndərin."
)

THANKS_WAIT = (
    "✅ Təşəkkür edirik! Ödənişiniz yoxlama üçün göndərildi. "
    "Zəhmət olmasa gözləyin — tezliklə sizə yazacağıq."
)

CONFIRMED = (
    "✅ Ödəniş təsdiqləndi! İndi «📦 Göndər PDF» düyməsini basın — faylı göndərim."
)

NOT_CONFIRMED = (
    "ℹ️ Ödənişiniz hələ yoxlanılır. Zəhmət olmasa gözləyin."
)

CONTACT_TEXT = (
    f"👤 Əlaqə üçün admin: @{ADMIN_USERNAME}"
)

HELP_TEXT = (
    "<b>🛠 Komandalar:</b>\n"
    "/id – öz ID'n\n"
    "/help – bu yardım\n"
    "<b>👑 Admin üçün:</b>\n"
    "Yeni ödəniş → təsdiq üçün inline düymələr admina gəlir\n"
    "Təsdiqdən sonra fayl: «📦 Göndər PDF»\n"
    "«Əlaqə» admin profilinə link\n"
)

# ---------- КЛАВИАТУРЫ ----------
user_kb = ReplyKeyboardMarkup(resize_keyboard=True)
user_kb.add(KeyboardButton("🧾 Yeni ödəniş"))
user_kb.add(KeyboardButton("📦 Göndər PDF"))
user_kb.add(KeyboardButton("👤 Əlaqə"))

# ---------- БОТ ----------
bot = Bot(TOKEN, parse_mode="HTML")
dp = Dispatcher(bot)

load_state()

# ---------- ХЭНДЛЕРЫ ----------
@dp.message_handler(commands=["start"])
async def start_cmd(m: types.Message):
    await m.answer(WELCOME, reply_markup=user_kb)

# любое сообщение от нового/старого юзера — показываем приветствие (как просил)
@dp.message_handler(regexp=r".*")
async def any_text(m: types.Message):
    txt = (m.text or "").strip().lower()
    if txt in ["🧾 yeni ödəniş", "yeni ödəniş", "yeni", "ödəniş"]:
        await m.answer("📷 Zəhmət olmasa ödəniş screenshot-u göndərin.", reply_markup=user_kb)
        return
    if txt in ["📦 göndər pdf", "göndər pdf", "pdf"]:
        # проверяем статус
        if is_approved(m.from_user.id):
            if not os.path.exists(PDF_FILE):
                await m.answer("⚠️ PDF faylı tapılmadı. Adminə yazın.", reply_markup=user_kb)
                return
            with open(PDF_FILE, "rb") as f:
                await m.answer_document(f)
        elif is_pending(m.from_user.id):
            await m.answer(NOT_CONFIRMED, reply_markup=user_kb)
        else:
            await m.answer("ℹ️ Əvvəlcə ödəniş screenshot-u göndərin.", reply_markup=user_kb)
        return
    if txt in ["👤 əlaqə", "əlaqə", "contact"]:
        await m.answer(CONTACT_TEXT, reply_markup=user_kb)
        return

    # по умолчанию — приветствие
    await m.answer(WELCOME, reply_markup=user_kb)

# фото/документы — считаем как чек
@dp.message_handler(content_types=["photo", "document"])
async def got_proof(m: types.Message):
    uid = m.from_user.id
    set_pending(uid)

    # уведомляем пользователя
    await m.answer(THANKS_WAIT, reply_markup=user_kb)

    # пробуем достать file_id для админа (чтобы открыть)
    caption = f"✅ Yeni ödəniş!\n\nUser: @{m.from_user.username or '—'}\nID: <code>{uid}</code>"

    kb = InlineKeyboardMarkup()
    kb.add(
        InlineKeyboardButton("✅ Təsdiqlə", callback_data=f"approve:{uid}"),
        InlineKeyboardButton("❌ Rədd et", callback_data=f"decline:{uid}")
    )

    if m.content_type == "photo":
        # самая большая по качеству
        file_id = m.photo[-1].file_id
        await bot.send_photo(ADMIN_ID, file_id, caption=caption, reply_markup=kb)
    else:
        await bot.send_document(ADMIN_ID, m.document.file_id, caption=caption, reply_markup=kb)

# --- админ: approve/decline ---
@dp.callback_query_handler(lambda c: c.data.startswith("approve:") or c.data.startswith("decline:"))
async def admin_decision(c: types.CallbackQuery):
    # кто жмёт?
    if str(c.from_user.id) != str(ADMIN_ID):
        await c.answer("Bu əmri yalnız admin üçündür.", show_alert=True)
        return

    action, uid_str = c.data.split(":")
    uid = int(uid_str)

    if action == "approve":
        approve(uid)
        await bot.send_message(uid, CONFIRMED, reply_markup=user_kb)
        await c.message.edit_reply_markup(reply_markup=None)
        await c.answer("Təsdiqləndi!", show_alert=False)
        log.info("Approved %s", uid)
    else:
        decline(uid)
        await bot.send_message(uid, "❌ Rədd edildi.", reply_markup=user_kb)
        await c.message.edit_reply_markup(reply_markup=None)
        await c.answer("Rədd edildi.", show_alert=False)
        log.info("Declined %s", uid)

# --- /id, /help (и только текст, для аккуратности) ---
@dp.message_handler(commands=["id"])
async def show_id(m: types.Message):
    await m.reply(f"Sənin ID-in: <code>{m.from_user.id}</code>")

@dp.message_handler(commands=["help"])
async def help_cmd(m: types.Message):
    await m.reply(HELP_TEXT)

# ---------- СТАРТ ----------
if __name__ == "__main__":
    log.info("🚀 Bot is starting...")
    executor.start_polling(dp, skip_updates=True)
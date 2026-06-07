#!/usr/bin/env python3
import asyncio
import logging
import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated
import os

# ========== КОНФИГУРАЦИЯ ==========
TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    raise RuntimeError("MAX_TOKEN не установлен в переменных окружения")

bot = Bot(token=TOKEN)
dp = Dispatcher()
logging.basicConfig(level=logging.INFO)

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect("formula100.db")
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            full_name TEXT,
            registered_at TIMESTAMP,
            gender TEXT,
            age INTEGER,
            goals TEXT,
            restrictions TEXT
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            product_id INTEGER,
            total_capsules INTEGER,
            used_capsules INTEGER,
            last_updated TIMESTAMP,
            PRIMARY KEY (user_id, product_id)
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS diary (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            date DATE,
            energy INTEGER,
            sleep INTEGER,
            mood INTEGER,
            notes TEXT
        )
    """)
    conn.commit()
    conn.close()
    logging.info("База данных инициализирована")

init_db()

# ========== ДАННЫЕ ТОВАРОВ ==========
PRODUCTS = {
    1: {"name": "MAXFIT Collagen 5800 мг", "article": "166219182", "price": 600, "daily_dosage": 2},
    2: {"name": "Maxler Energy and Focus", "article": "65011520", "price": 1200, "daily_dosage": 2},
    3: {"name": "Aksu vital Омега-3-6-9", "article": "192381456", "price": 900, "daily_dosage": 2},
    4: {"name": "Синбиотик Будь здоров!", "article": "149215284", "price": 700, "daily_dosage": 2},
    5: {"name": "Экстракт чёрного перца 95%", "article": "155252287", "price": 400, "daily_dosage": 1},
    6: {"name": "Магний + B6 (ZMA)", "article": "search_by_name", "price": 1500, "daily_dosage": 3},
    7: {"name": "Ноотроп Память (ВИС)", "article": "170419677", "price": 500, "daily_dosage": 2},
    8: {"name": "VPLab Tribulus + Zinc", "article": "175879624", "price": 800, "daily_dosage": 2},
    9: {"name": "Геладринк Форте", "article": "183227957", "price": 1100, "daily_dosage": 1},
}

# ========== ЛОГИКА ПОДБОРА ==========
def get_recommendation(goals: List[str]) -> List[int]:
    """Возвращает список ID продуктов на основе целей"""
    base = [1, 3, 4, 5, 6]  # всегда коллаген, омега, синбиотик, пиперин, магний
    extra = []
    if "энергия" in goals:
        extra.append(2)
    if "память" in goals or "мозг" in goals:
        extra.append(7)
    if "либидо" in goals:
        extra.append(8)
    if "суставы" in goals:
        extra.append(9)
    # убираем дубликаты и сохраняем порядок
    seen = set()
    recs = []
    for pid in base + extra:
        if pid not in seen:
            seen.add(pid)
            recs.append(pid)
    return recs

def format_recommendation(product_ids: List[int]) -> str:
    lines = ["📋 *Ваш персональный набор:*\n"]
    total = 0
    for pid in product_ids:
        p = PRODUCTS.get(pid)
        if p:
            lines.append(f"• {p['name']} — арт. `{p['article']}` — {p['price']} руб.")
            total += p['price']
    lines.append(f"\n💰 *Примерная стоимость:* {total} руб.")
    lines.append("\n⚠️ Рекомендация основана на ваших целях. Проконсультируйтесь с врачом.")
    return "\n".join(lines)

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ БД ==========
def save_user(user_id: int, username: str, full_name: str):
    conn = sqlite3.connect("formula100.db")
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id, username, full_name, registered_at) VALUES (?, ?, ?, ?)",
              (user_id, username, full_name, datetime.now()))
    conn.commit()
    conn.close()

def update_user_questionnaire(user_id: int, gender: str, age: int, goals: List[str], restrictions: List[str]):
    conn = sqlite3.connect("formula100.db")
    c = conn.cursor()
    c.execute("UPDATE users SET gender=?, age=?, goals=?, restrictions=? WHERE user_id=?",
              (gender, age, ",".join(goals), ",".join(restrictions), user_id))
    conn.commit()
    conn.close()

def get_user_goals(user_id: int) -> Optional[List[str]]:
    conn = sqlite3.connect("formula100.db")
    c = conn.cursor()
    c.execute("SELECT goals FROM users WHERE user_id=?", (user_id,))
    row = c.fetchone()
    conn.close()
    if row and row[0]:
        return row[0].split(",")
    return None

def add_diary_entry(user_id: int, energy: int, sleep: int, mood: int, notes: str = ""):
    conn = sqlite3.connect("formula100.db")
    c = conn.cursor()
    today = datetime.now().date().isoformat()
    c.execute("INSERT INTO diary (user_id, date, energy, sleep, mood, notes) VALUES (?, ?, ?, ?, ?, ?)",
              (user_id, today, energy, sleep, mood, notes))
    conn.commit()
    conn.close()

def get_inventory(user_id: int) -> List[Tuple]:
    conn = sqlite3.connect("formula100.db")
    c = conn.cursor()
    c.execute("""
        SELECT p.name, i.total_capsules, i.used_capsules, p.daily_dosage
        FROM inventory i JOIN products p ON i.product_id = p.id
        WHERE i.user_id = ?
    """, (user_id,))
    data = c.fetchall()
    conn.close()
    return data

def add_to_inventory(user_id: int, product_id: int, capsules: int):
    conn = sqlite3.connect("formula100.db")
    c = conn.cursor()
    c.execute("""
        INSERT INTO inventory (user_id, product_id, total_capsules, used_capsules, last_updated)
        VALUES (?, ?, ?, 0, ?)
        ON CONFLICT(user_id, product_id) DO UPDATE SET
            total_capsules = total_capsules + ?,
            last_updated = ?
    """, (user_id, product_id, capsules, datetime.now(), capsules, datetime.now()))
    conn.commit()
    conn.close()

# ========== ОБРАБОТЧИКИ СОБЫТИЙ ==========
# Состояния для анкеты (храним в словаре, т.к. maxapi не имеет встроенного FSM, но можно использовать простой dict)
user_states = {}  # {user_id: {'step': str, 'data': dict}}

@dp.bot_started()
async def on_bot_started(event: BotStarted):
    chat_id = event.chat_id
    user_id = event.user_id
    # Сохраняем пользователя
    save_user(user_id, "", "")  # username/full_name можно получить позже
    await bot.send_message(chat_id=chat_id, text="🧬 *Formula 100 AI*\n\nПривет! Я помогу подобрать БАДы и вести дневник здоровья.\nИспользуй /help для списка команд.", parse_mode="markdown")

@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    chat_id = event.message.recipient.chat_id
    user_id = event.message.recipient.user_id
    save_user(user_id, "", "")
    await bot.send_message(chat_id=chat_id, text="Добро пожаловать! Напиши /help чтобы узнать команды.")

@dp.message_created(Command('help'))
async def cmd_help(event: MessageCreated):
    chat_id = event.message.recipient.chat_id
    await bot.send_message(chat_id=chat_id, text="""
📖 *Команды:*
/questionnaire — пройти анкету (нужно для рекомендаций)
/recommend — получить персональный набор БАД
/inventory — остатки капсул (учёт)
/diary — дневник самочувствия (энергия, сон, настроение)
/add_product — добавить купленный товар в инвентарь
/help — эта справка
""", parse_mode="markdown")

# ========== АНКЕТА (многошаговая) ==========
@dp.message_created(Command('questionnaire'))
async def cmd_questionnaire(event: MessageCreated):
    chat_id = event.message.recipient.chat_id
    user_id = event.message.recipient.user_id
    user_states[user_id] = {"step": "gender", "data": {}}
    await bot.send_message(chat_id=chat_id, text="Давай познакомимся. Твой пол? (М/Ж)")

@dp.message_created()
async def handle_questionnaire(event: MessageCreated):
    user_id = event.message.recipient.user_id
    if user_id not in user_states:
        return  # не в режиме анкеты
    state = user_states[user_id]
    step = state["step"]
    text = event.message.body.text.strip().lower()
    chat_id = event.message.recipient.chat_id

    if step == "gender":
        if text in ("м", "ж", "мж", "мужской", "женский"):
            gender = "м" if text in ("м", "мужской") else "ж"
            state["data"]["gender"] = gender
            state["step"] = "age"
            await bot.send_message(chat_id=chat_id, text="Твой возраст? (число)")
        else:
            await bot.send_message(chat_id=chat_id, text="Пожалуйста, ответь М или Ж.")
    elif step == "age":
        if text.isdigit():
            age = int(text)
            state["data"]["age"] = age
            state["step"] = "goals"
            await bot.send_message(chat_id=chat_id, text="Какие цели? Можно перечислить через запятую: энергия, память, либидо, суставы, кожа, сон")
        else:
            await bot.send_message(chat_id=chat_id, text="Введи число (возраст).")
    elif step == "goals":
        goals = [g.strip() for g in text.split(",")]
        state["data"]["goals"] = goals
        state["step"] = "restrictions"
        await bot.send_message(chat_id=chat_id, text="Есть ли ограничения? (например, аллергия, гипертония, нет кофеину). Если нет, напиши /skip")
    elif step == "restrictions":
        if text == "/skip":
            restrictions = []
        else:
            restrictions = [text]
        state["data"]["restrictions"] = restrictions
        # сохраняем в БД
        update_user_questionnaire(user_id, state["data"].get("gender", ""), state["data"].get("age", 0),
                                  state["data"].get("goals", []), restrictions)
        await bot.send_message(chat_id=chat_id, text="✅ Анкета сохранена! Теперь можешь получить рекомендацию командой /recommend")
        del user_states[user_id]

# ========== РЕКОМЕНДАЦИЯ ==========
@dp.message_created(Command('recommend'))
async def cmd_recommend(event: MessageCreated):
    user_id = event.message.recipient.user_id
    chat_id = event.message.recipient.chat_id
    goals = get_user_goals(user_id)
    if not goals:
        await bot.send_message(chat_id=chat_id, text="Сначала пройди анкету: /questionnaire")
        return
    rec_ids = get_recommendation(goals)
    answer = format_recommendation(rec_ids)
    await bot.send_message(chat_id=chat_id, text=answer, parse_mode="markdown")

# ========== ДНЕВНИК ==========
@dp.message_created(Command('diary'))
async def cmd_diary(event: MessageCreated):
    user_id = event.message.recipient.user_id
    chat_id = event.message.recipient.chat_id
    await bot.send_message(chat_id=chat_id, text="Введи три числа через пробел: энергия (1-10) сон (1-10) настроение (1-10)\nПример: 8 7 9\nМожно добавить комментарий после.")

    # сохраняем состояние, что ждём ввода дневника
    user_states[user_id] = {"step": "diary_input"}

# обработчик ввода дневника (после команды /diary)
@dp.message_created()
async def handle_diary_input(event: MessageCreated):
    user_id = event.message.recipient.user_id
    if user_id not in user_states or user_states[user_id].get("step") != "diary_input":
        return
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text
    parts = text.split()
    if len(parts) < 3:
        await bot.send_message(chat_id=chat_id, text="Нужно три числа. Попробуй ещё раз.")
        return
    try:
        energy = int(parts[0])
        sleep = int(parts[1])
        mood = int(parts[2])
        notes = " ".join(parts[3:]) if len(parts) > 3 else ""
        add_diary_entry(user_id, energy, sleep, mood, notes)
        await bot.send_message(chat_id=chat_id, text="✅ Дневник сохранён! Спасибо.")
        del user_states[user_id]
    except ValueError:
        await bot.send_message(chat_id=chat_id, text="Ошибка: все три значения должны быть числами.")

# ========== ИНВЕНТАРЬ ==========
@dp.message_created(Command('inventory'))
async def cmd_inventory(event: MessageCreated):
    user_id = event.message.recipient.user_id
    chat_id = event.message.recipient.chat_id
    inv = get_inventory(user_id)
    if not inv:
        await bot.send_message(chat_id=chat_id, text="У тебя пока нет добавленных товаров. Используй /add_product для добавления.")
        return
    text = "📦 *Твои запасы:*\n"
    for name, total, used, daily in inv:
        remaining = total - used
        days = remaining // daily if daily > 0 else 0
        text += f"• {name}: осталось {remaining} капс. (~{days} дней)\n"
    await bot.send_message(chat_id=chat_id, text=text, parse_mode="markdown")

@dp.message_created(Command('add_product'))
async def cmd_add_product(event: MessageCreated):
    user_id = event.message.recipient.user_id
    chat_id = event.message.recipient.chat_id
    # Создаём клавиатуру с товарами (простая текстовая, но MAX поддерживает inline-кнопки? maxapi пока не умеет, поэтому попросим ввести ID)
    # Для простоты пока попросим выбрать из списка.
    product_list = "\n".join([f"{pid}. {p['name']}" for pid, p in PRODUCTS.items()])
    await bot.send_message(chat_id=chat_id, text=f"Введи ID товара из списка:\n{product_list}\nПример: 1")
    user_states[user_id] = {"step": "add_product_id"}

@dp.message_created()
async def handle_add_product(event: MessageCreated):
    user_id = event.message.recipient.user_id
    if user_id not in user_states or user_states[user_id].get("step") != "add_product_id":
        return
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text
    if not text.isdigit():
        await bot.send_message(chat_id=chat_id, text="Введи число (ID товара).")
        return
    prod_id = int(text)
    if prod_id not in PRODUCTS:
        await bot.send_message(chat_id=chat_id, text="Неверный ID. Попробуй ещё раз.")
        return
    user_states[user_id]["product_id"] = prod_id
    user_states[user_id]["step"] = "add_product_capsules"
    await bot.send_message(chat_id=chat_id, text="Сколько капсул в упаковке? (целое число)")

@dp.message_created()
async def handle_add_product_capsules(event: MessageCreated):
    user_id = event.message.recipient.user_id
    if user_id not in user_states or user_states[user_id].get("step") != "add_product_capsules":
        return
    chat_id = event.message.recipient.chat_id
    text = event.message.body.text
    if not text.isdigit():
        await bot.send_message(chat_id=chat_id, text="Введи целое число капсул.")
        return
    capsules = int(text)
    prod_id = user_states[user_id]["product_id"]
    add_to_inventory(user_id, prod_id, capsules)
    await bot.send_message(chat_id=chat_id, text=f"✅ {capsules} капсул добавлено в инвентарь.")
    del user_states[user_id]

# ========== ЗАПУСК БОТА ==========
async def main():
    logging.info("Запуск бота...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

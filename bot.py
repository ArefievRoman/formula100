#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import aiohttp
import os
import json
import sqlite3
from datetime import datetime
from typing import Optional, Dict, Any, List

# ==================== НАСТРОЙКИ ====================
TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("❌ ОШИБКА: Переменная окружения MAX_TOKEN не установлена!")
    exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

# ==================== БАЗА ДАННЫХ ====================
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
        CREATE TABLE IF NOT EXISTS recommendations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            product_ids TEXT,
            issued_at TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    print("✅ База данных готова")

init_db()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def api_request(method: str, endpoint: str, data: Optional[Dict] = None) -> Optional[Dict]:
    """Универсальная функция для запросов к API MAX"""
    url = f"{BASE_URL}/{endpoint}"
    async with aiohttp.ClientSession() as session:
        async with session.request(method, url, headers=HEADERS, json=data) as resp:
            if resp.status == 200:
                return await resp.json()
            else:
                text = await resp.text()
                print(f"Ошибка API {endpoint}: {resp.status} - {text}")
                return None

async def send_message(chat_id: int, text: str) -> bool:
    """Отправить сообщение пользователю"""
    result = await api_request("POST", "sendMessage", {"chat_id": chat_id, "text": text})
    return result is not None

async def get_updates(offset: Optional[int] = None) -> List[Dict]:
    """Получить новые сообщения (long polling)"""
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    result = await api_request("GET", "updates", data=params)
    if result and "updates" in result:
        return result["updates"]
    return []

# ==================== ЛОГИКА ПОДБОРА ====================
PRODUCTS = {
    1: {"name": "MAXFIT Collagen 5800 мг", "price": 600, "article": "166219182"},
    2: {"name": "Maxler Energy and Focus", "price": 1200, "article": "65011520"},
    3: {"name": "Омега-3-6-9", "price": 900, "article": "192381456"},
    4: {"name": "Синбиотик Будь здоров!", "price": 700, "article": "149215284"},
    5: {"name": "Экстракт чёрного перца", "price": 400, "article": "155252287"},
    6: {"name": "Магний + B6 (ZMA)", "price": 1500, "article": "search"},
    7: {"name": "Ноотроп Память", "price": 500, "article": "170419677"},
}

def get_recommendation(goals: list) -> list:
    # Базовый набор для всех
    base = [1, 3, 4, 5]
    # Дополнительные карточки в зависимости от целей
    extra = []
    if "энергия" in goals:
        extra.append(2)
    if "память" in goals or "мозг" in goals:
        extra.append(7)
    if "суставы" in goals:
        extra.append(6)
    # Убираем дубликаты
    return list(dict.fromkeys(base + extra))

def format_recommendation(product_ids: list) -> str:
    lines = ["📋 *Ваш персональный набор:*\n"]
    total = 0
    for pid in product_ids:
        p = PRODUCTS.get(pid)
        if p:
            lines.append(f"• {p['name']} — арт. `{p['article']}` — {p['price']} руб.")
            total += p['price']
    lines.append(f"\n💰 *Примерная стоимость:* {total} руб.")
    lines.append("\n⚠️ Все рекомендации – информационные. Проконсультируйтесь с врачом.")
    return "\n".join(lines)

# ==================== ОБРАБОТЧИК СООБЩЕНИЙ ====================
async def handle_message(chat_id: int, text: str, user_data: Dict[int, Any]):
    """Обработка команд и текста"""
    if text == "/start":
        await send_message(chat_id, "🧬 *Formula 100 AI*\n\nПривет! Я помогу подобрать БАДы.\nИспользуй команду /help для списка.")
        # Сохраняем пользователя
        conn = sqlite3.connect("formula100.db")
        c = conn.cursor()
        c.execute("INSERT OR IGNORE INTO users (user_id, registered_at) VALUES (?, ?)", (chat_id, datetime.now()))
        conn.commit()
        conn.close()
        return

    if text == "/help":
        await send_message(chat_id, "📖 *Команды:*\n/questionnaire – анкета\n/recommend – рекомендация\n/inventory – мои запасы\n/help – справка")
        return

    if text == "/questionnaire":
        # Начинаем анкету (храним состояние в памяти)
        user_data[chat_id] = {"step": "gender"}
        await send_message(chat_id, "Укажите ваш пол (М/Ж):")
        return

    if text == "/recommend":
        conn = sqlite3.connect("formula100.db")
        c = conn.cursor()
        c.execute("SELECT goals FROM users WHERE user_id=?", (chat_id,))
        row = c.fetchone()
        conn.close()
        if not row or not row[0]:
            await send_message(chat_id, "Сначала заполните анкету командой /questionnaire")
            return
        goals = row[0].split(",")
        rec = get_recommendation(goals)
        await send_message(chat_id, format_recommendation(rec))
        return

    if text == "/inventory":
        await send_message(chat_id, "Функция учёта запасов в разработке. Скоро добавим!")
        return

    # Обработка шагов анкеты (простой конечный автомат)
    if chat_id in user_data:
        step = user_data[chat_id]["step"]
        if step == "gender":
            if text.lower() in ["м", "ж", "мж", "женский", "мужской"]:
                gender = "м" if text.lower() in ["м", "мужской"] else "ж"
                user_data[chat_id]["gender"] = gender
                user_data[chat_id]["step"] = "age"
                await send_message(chat_id, "Сколько вам лет?")
            else:
                await send_message(chat_id, "Пожалуйста, введите М или Ж")
        elif step == "age":
            if text.isdigit():
                age = int(text)
                user_data[chat_id]["age"] = age
                user_data[chat_id]["step"] = "goals"
                await send_message(chat_id, "Какие цели? Введите через запятую: энергия, память, суставы, кожа, сон, либидо")
            else:
                await send_message(chat_id, "Введите возраст цифрами")
        elif step == "goals":
            goals = [g.strip().lower() for g in text.split(",")]
            # Сохраняем в БД
            conn = sqlite3.connect("formula100.db")
            c = conn.cursor()
            c.execute("UPDATE users SET gender=?, age=?, goals=? WHERE user_id=?",
                      (user_data[chat_id]["gender"], user_data[chat_id]["age"], ",".join(goals), chat_id))
            conn.commit()
            conn.close()
            del user_data[chat_id]
            await send_message(chat_id, "✅ Анкета сохранена! Теперь можете получить рекомендацию: /recommend")
        else:
            # Неизвестный шаг – сброс
            del user_data[chat_id]
    else:
        await send_message(chat_id, "Я вас не понял. Напишите /help для списка команд.")

# ==================== ГЛАВНЫЙ ЦИКЛ (POLLING) ====================
async def main():
    print("🚀 Бот запущен и ожидает сообщений...")
    user_states = {}  # временное хранилище для анкет
    last_update_id = 0
    while True:
        updates = await get_updates(offset=last_update_id + 1 if last_update_id else None)
        for upd in updates:
            # Проверяем наличие сообщения
            msg = upd.get("message")
            if msg and isinstance(msg, dict):
                chat = msg.get("chat")
                if chat and "id" in chat:
                    chat_id = chat["id"]
                    text = msg.get("text", "")
                    if text:
                        await handle_message(chat_id, text, user_states)
                else:
                    print("Пропущено обновление без chat_id")
            # Обновляем offset
            if "update_id" in upd:
                last_update_id = upd["update_id"]
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен")

#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import json
import sqlite3
from datetime import datetime
from typing import Dict, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn
import aiohttp

# ==================== КОНФИГУРАЦИЯ ====================
MAX_TOKEN = "f9LHodD0cOIBqiz68b2fIVi8e3UZ4V9DZueBGWc_pxKgtGhxh8DLHbmX5iGofyZizBrG9GPiF9YacLbixLvQ"
PUBLIC_URL = "https://bot-1780836164-3415-arefev-roman.bothost.tech"

MAX_API_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": MAX_TOKEN, "Content-Type": "application/json"}

# ==================== БАЗА ДАННЫХ ====================
DB_PATH = "formula100.db"

def init_db():
    """Инициализирует базу данных SQLite, создавая таблицы, если их нет."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            first_name TEXT,
            registered_at TIMESTAMP,
            last_activity TIMESTAMP
        )
    """)
    c.execute("""
        CREATE TABLE IF NOT EXISTS social_interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            person_name TEXT,
            role TEXT,
            aggression INTEGER,
            intelligence INTEGER,
            positivity INTEGER,
            event_desc TEXT,
            timestamp TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def send_message(user_id: int, text: str, parse_mode: str = "markdown"):
    """Отправляет сообщение пользователю."""
    url = f"{MAX_API_URL}/messages"
    payload = {
        "recipient": {"user_id": user_id},
        "body": {"text": text}
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                err = await resp.text()
                print(f"send_message error {resp.status}: {err}")
            else:
                print(f"Сообщение отправлено пользователю {user_id}")

# ==================== МОДУЛЬ WILDBERRIES ====================
async def fetch_wb_product(article: str) -> Optional[Dict]:
    """Получает информацию о товаре с Wildberries по артикулу."""
    url = f"https://card.wb.ru/cards/v2/detail?nmId={article}"
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if data and 'data' in data and 'products' in data['data'] and data['data']['products']:
                        p = data['data']['products'][0]
                        return {
                            'name': p.get('name', 'Неизвестно'),
                            'brand': p.get('brand', 'Неизвестно'),
                            'price': p.get('priceU', 0) // 100,
                            'rating': p.get('rating', 0),
                            'feedbacks': p.get('feedbacks', 0),
                            'url': f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
                        }
                return None
        except Exception as e:
            print(f"WB error: {e}")
            return None

# ==================== СОЦИАЛЬНЫЙ ГРАФ ====================
async def save_interaction(user_id: int, person: str, role: str, agg: int, intel: int, pos: int, desc: str):
    """Сохраняет запись о социальном взаимодействии в базу данных."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO social_interactions (user_id, person_name, role, aggression, intelligence, positivity, event_desc, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, person, role, agg, intel, pos, desc, datetime.now()))
    conn.commit()
    conn.close()

async def predict_relationship(user_id: int, person: str) -> Dict:
    """Анализирует историю взаимодействий и делает прогноз."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT aggression, positivity, timestamp
        FROM social_interactions
        WHERE user_id=? AND person_name=?
        ORDER BY timestamp ASC
    """, (user_id, person))
    rows = c.fetchall()
    conn.close()

    if len(rows) < 2:
        return {'prediction': 'Недостаточно данных', 'advice': 'Продолжайте общаться и фиксировать взаимодействия', 'confidence': 0.5}
    
    agg_start, agg_end = rows[0][0], rows[-1][0]
    pos_start, pos_end = rows[0][1], rows[-1][1]

    if agg_end < agg_start and pos_end > pos_start:
        return {'prediction': 'Отношения улучшаются', 'advice': 'Отлично, продолжайте в том же духе!', 'confidence': 0.75}
    elif agg_end > agg_start and pos_end < pos_start:
        return {'prediction': 'Отношения ухудшаются', 'advice': 'Попробуйте изменить тактику общения', 'confidence': 0.7}
    else:
        return {'prediction': 'Стабильно', 'advice': 'Обратите внимание на мелочи, они важны', 'confidence': 0.6}

# ==================== ГЕНЕРАЦИЯ МЕНЮ ====================
async def generate_daily_menu(user_id: int) -> str:
    """Генерирует текст ежедневного меню."""
    base = [
        "🌅 *Утро (натощак)*: MAXFIT Collagen 5800 мг",
        "🌞 *День*: Омега-3-6-9 – 2 капсулы",
        "🌙 *Вечер*: Синбиотик – 2 капсулы",
        "🧠 *Ноотроп*: Ноотроп Память – 2 капсулы утром"
    ]
    menu = "\n".join(base)
    menu += "\n\n💧 *Важно*: пейте не менее 2 л воды в день!"
    return menu

# ==================== ОБРАБОТЧИК СООБЩЕНИЙ ====================
async def handle_update(update: Dict):
    """Основная функция для обработки входящих обновлений (сообщений)."""
    print(f"🔔 Получен update: {json.dumps(update, ensure_ascii=False)[:300]}")
    
    message = update.get('message')
    if not message:
        print("Нет поля message")
        return

    sender = message.get('sender')
    if not sender:
        print("Нет поля sender")
        return

    user_id = sender.get('user_id')
    if not user_id:
        print("Нет user_id в sender")
        return

    body = message.get('body', {})
    text = body.get('text', '')
    
    if not text:
        print("Нет текста")
        return

    print(f"Обработка сообщения от пользователя {user_id}: {text}")
    
    # Обновляем время последней активности пользователя в БД
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, last_activity) VALUES (?, ?)", (user_id, datetime.now()))
    conn.commit()
    conn.close()
    
    # Обработка команд
    if not text.startswith('/'):
        await send_message(user_id, "Используйте команды из /help")
        return
    
    parts = text.split()
    cmd = parts[0].lower()
    
    if cmd == '/start':
        await send_message(user_id,
            "🧬 *Formula 100 AI*\n\nПривет! Я AI-помощник по здоровью.\n\n"
            "📌 *Команды:*\n"
            "/wb <артикул> – информация о товаре на Wildberries\n"
            "/daily – персональное меню на сегодня\n"
            "/social <имя> <роль> <агрессия(1-10)> <интеллект(1-10)> <позитив(1-10)> <событие>\n"
            "/predict <имя> – прогноз развития отношений\n"
            "/help – справка")
            
    elif cmd == '/help':
        await send_message(user_id, "📖 *Справка*\n/start – приветствие\n/wb – товар\n/daily – меню\n/social – записать\n/predict – прогноз")
        
    elif cmd == '/wb':
        if len(parts) < 2:
            await send_message(user_id, "❌ Укажите артикул: /wb 12345678")
        else:
            article = parts[1]
            await send_message(user_id, f"🔍 Ищу товар {article}...")
            prod = await fetch_wb_product(article)
            if prod:
                msg = (f"📦 *{prod['name']}*\n🏷 Бренд: {prod['brand']}\n💰 Цена: {prod['price']} руб.\n"
                       f"⭐ Рейтинг: {prod['rating']}\n📝 Отзывов: {prod['feedbacks']}\n🔗 [Ссылка]({prod['url']})")
                await send_message(user_id, msg)
            else:
                await send_message(user_id, "❌ Товар не найден")
                
    elif cmd == '/daily':
        menu = await generate_daily_menu(user_id)
        await send_message(user_id, menu)
        
    elif cmd == '/social':
        if len(parts) < 7:
            await send_message(user_id, "❌ Формат: /social <имя> <роль> <агрессия> <интеллект> <позитив> <событие>")
        else:
            _, name, role, agg_str, intel_str, pos_str, event = parts[1:]
            try:
                agg = int(agg_str)
                intel = int(intel_str)
                pos = int(pos_str)
                if not (1 <= agg <= 10 and 1 <= intel <= 10 and 1 <= pos <= 10):
                    raise ValueError
            except ValueError:
                await send_message(user_id, "❌ Оценки должны быть числами от 1 до 10")
                return
            
            await save_interaction(user_id, name, role, agg, intel, pos, event)
            await send_message(user_id, f"✅ Взаимодействие с {name} сохранено")
            
    elif cmd == '/predict':
        if len(parts) < 2:
            await send_message(user_id, "❌ Укажите имя: /predict Иван")
        else:
            name = parts[1]
            pred = await predict_relationship(user_id, name)
            await send_message(user_id,
                f"🔮 *Прогноз отношений с {name}*\n📈 {pred['prediction']}\n💡 {pred['advice']}\n🎯 Уверенность: {pred.get('confidence',0.5)*100:.0f}%")
                
    else:
        await send_message(user_id, "Неизвестная команда. /help")

# ==================== FASTAPI WEBHOOK ====================
app = FastAPI()

@app.post("/webhook")
async def webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
    """Точка входа для вебхуков от платформы."""
    try:
        update = await request.json()
    except Exception as e:
        print(f"Ошибка парсинга JSON: {e}")
        return Response(status_code=400)
    
    # Обработка происходит в фоновом потоке.
    background_tasks.add_task(handle_update, update)
    
    return JSONResponse({"status": "ok"})

@app.get("/")
async def root():
    """Простой хелсчек для проверки работоспособности сервера."""
    return {"status": "alive"}

# ==================== УСТАНОВКА ВЕБХУКА ====================
async def set_webhook():
    """
    Устанавливает вебхук.
    Ключевое изменение: добавлен параметр `scope: "unicast"` для получения сообщений от пользователей.
    """
    webhook_url = f"{PUBLIC_URL.rstrip('/')}/webhook"
    
    url = f"{MAX_API_URL}/subscriptions"
    
    payload = {
        "url": webhook_url,
        "update_types": ["message_created"],
        
        # --- ИЗМЕНЕНИЕ ЗДЕСЬ ---
        "scope": "unicast"
        # ---------------------
        
    }
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                print(f"✅ Вебхук установлен: {webhook_url}")
                # Для отладки можно вывести текст ответа от платформы
                # print(await resp.text())
            else:
                text = await resp.text()
                print(f"❌ Ошибка установки вебхука: {resp.status} - {text}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Функция жизненного цикла FastAPI. Выполняется при старте приложения."""
    await set_webhook()
    
app.router.lifespan_context = lifespan

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    
    # Запускаем сервер Uvicorn.
    uvicorn.run(app, host="0.0.0.0", port=port)

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
async def send_message(chat_id: int, text: str, parse_mode: str = "markdown"):
    """Отправка сообщения через правильный эндпоинт /messages"""
    url = f"{MAX_API_URL}/messages"
    payload = {
        "recipient": {"chat_id": chat_id},
        "body": {"text": text}
    }
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                err = await resp.text()
                print(f"send_message error {resp.status}: {err}")
            else:
                print(f"Сообщение отправлено в чат {chat_id}")

# ==================== МОДУЛЬ WILDBERRIES ====================
async def fetch_wb_product(article: str) -> Optional[Dict]:
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
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        INSERT INTO social_interactions (user_id, person_name, role, aggression, intelligence, positivity, event_desc, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (user_id, person, role, agg, intel, pos, desc, datetime.now()))
    conn.commit()
    conn.close()

async def predict_relationship(user_id: int, person: str) -> Dict:
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
    print(f"🔔 Получен update: {json.dumps(update, ensure_ascii=False)}")
    message = update.get('message')
    if not message:
        print("Нет поля message")
        return
    recipient = message.get('recipient')
    if not recipient:
        print("Нет поля recipient")
        return
    chat_id = recipient.get('chat_id')
    if not chat_id:
        print("Нет chat_id")
        return
    body = message.get('body', {})
    text = body.get('text', '')
    if not text:
        print("Нет текста")
        return
    print(f"Обработка сообщения от {chat_id}: {text}")
    
    # Обновляем активность
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, last_activity) VALUES (?, ?)", (chat_id, datetime.now()))
    conn.commit()
    conn.close()
    
    if not text.startswith('/'):
        await send_message(chat_id, "Используйте команды из /help")
        return
    
    parts = text.split()
    cmd = parts[0].lower()
    
    if cmd == '/start':
        await send_message(chat_id,
            "🧬 *Formula 100 AI*\n\nПривет! Я AI-помощник по здоровью.\n\n"
            "📌 *Команды:*\n"
            "/wb <артикул> – информация о товаре на Wildberries\n"
            "/daily – персональное меню на сегодня\n"
            "/social <имя> <роль> <агрессия(1-10)> <интеллект(1-10)> <позитив(1-10)> <событие>\n"
            "/predict <имя> – прогноз развития отношений\n"
            "/help – справка")
    elif cmd == '/help':
        await send_message(chat_id, "📖 *Справка*\n/start – приветствие\n/wb – товар\n/daily – меню\n/social – записать\n/predict – прогноз")
    elif cmd == '/wb':
        if len(parts) < 2:
            await send_message(chat_id, "❌ Укажите артикул: /wb 12345678")
        else:
            article = parts[1]
            await send_message(chat_id, f"🔍 Ищу товар {article}...")
            prod = await fetch_wb_product(article)
            if prod:
                msg = (f"📦 *{prod['name']}*\n🏷 Бренд: {prod['brand']}\n💰 Цена: {prod['price']} руб.\n"
                       f"⭐ Рейтинг: {prod['rating']}\n📝 Отзывов: {prod['feedbacks']}\n🔗 [Ссылка]({prod['url']})")
                await send_message(chat_id, msg)
            else:
                await send_message(chat_id, "❌ Товар не найден")
    elif cmd == '/daily':
        menu = await generate_daily_menu(chat_id)
        await send_message(chat_id, menu)
    elif cmd == '/social':
        if len(parts) < 7:
            await send_message(chat_id, "❌ Формат: /social <имя> <роль> <агрессия> <интеллект> <позитив> <событие>")
        else:
            _, name, role, agg_str, intel_str, pos_str, event = parts
            try:
                agg = int(agg_str)
                intel = int(intel_str)
                pos = int(pos_str)
                if not (1 <= agg <= 10 and 1 <= intel <= 10 and 1 <= pos <= 10):
                    raise ValueError
            except:
                await send_message(chat_id, "❌ Оценки должны быть числами от 1 до 10")
                return
            await save_interaction(chat_id, name, role, agg, intel, pos, event)
            await send_message(chat_id, f"✅ Взаимодействие с {name} сохранено")
    elif cmd == '/predict':
        if len(parts) < 2:
            await send_message(chat_id, "❌ Укажите имя: /predict Иван")
        else:
            name = parts[1]
            pred = await predict_relationship(chat_id, name)
            await send_message(chat_id,
                f"🔮 *Прогноз отношений с {name}*\n📈 {pred['prediction']}\n💡 {pred['advice']}\n🎯 Уверенность: {pred.get('confidence',0.5)*100:.0f}%")
    else:
        await send_message(chat_id, "Неизвестная команда. /help")

# ==================== FASTAPI WEBHOOK ====================
app = FastAPI()

@app.post("/webhook")
async def webhook_endpoint(request: Request, background_tasks: BackgroundTasks):
    try:
        update = await request.json()
    except:
        return Response(status_code=400)
    background_tasks.add_task(handle_update, update)
    return JSONResponse({"status": "ok"})

@app.get("/")
async def root():
    return {"status": "alive"}

# ==================== УСТАНОВКА ВЕБХУКА ====================
async def set_webhook():
    webhook_url = f"{PUBLIC_URL.rstrip('/')}/webhook"
    url = f"{MAX_API_URL}/subscriptions"
    payload = {"url": webhook_url, "update_types": ["message_created"]}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                print(f"✅ Вебхук установлен: {webhook_url}")
            else:
                text = await resp.text()
                print(f"❌ Ошибка установки вебхука: {resp.status} - {text}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    await set_webhook()
    yield

app.router.lifespan_context = lifespan

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)

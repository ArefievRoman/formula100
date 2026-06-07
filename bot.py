#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FORMULA 100 AI – Полнофункциональный бот для MAX
Поддерживает: текст, голос, Wildberries, соц. граф, прогнозы, меню
"""

import os
import re
import json
import sqlite3
import asyncio
import aiohttp
import aiofiles
import tempfile
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List, Tuple
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response, BackgroundTasks
from fastapi.responses import JSONResponse
import uvicorn

# ==================== КОНФИГУРАЦИЯ ====================
MAX_TOKEN = os.getenv("MAX_TOKEN")
if not MAX_TOKEN:
    raise RuntimeError("MAX_TOKEN not set")

# Опциональные ключи (можно оставить пустыми – будут работать заглушки)
VK_API_KEY = os.getenv("VK_API_KEY", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")

# Базовые URL
MAX_API_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": MAX_TOKEN, "Content-Type": "application/json"}

# Настройки бота
BOT_USERNAME = "id524619721097_1_bot"  # из логов, замени если нужно
WEBHOOK_PATH = "/webhook"

# ==================== БАЗА ДАННЫХ ====================
DB_PATH = "formula100.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    # Пользователи
    c.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            registered_at TIMESTAMP,
            last_activity TIMESTAMP,
            gender TEXT,
            age INTEGER,
            goals TEXT,
            restrictions TEXT,
            health_data TEXT
        )
    """)
    # Социальные взаимодействия
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
    # Инвентарь (упрощённо)
    c.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            user_id INTEGER,
            product_name TEXT,
            total_capsules INTEGER,
            used_capsules INTEGER,
            last_updated TIMESTAMP,
            PRIMARY KEY (user_id, product_name)
        )
    """)
    conn.commit()
    conn.close()

init_db()

# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
async def send_message(chat_id: int, text: str, parse_mode: str = "markdown"):
    """Отправка сообщения через API MAX"""
    url = f"{MAX_API_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text, "parse_mode": parse_mode}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                err = await resp.text()
                print(f"[send_message] error {resp.status}: {err}")

# ==================== МОДУЛЬ WILDBERRIES ====================
async def fetch_wb_product(article: str) -> Optional[Dict]:
    """
    Получает данные о товаре с Wildberries через публичный API.
    Возвращает словарь с полями: name, brand, price, rating, feedbacks, url
    """
    # Используем публичный API карточек товаров
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
                            'sale_price': p.get('salePriceU', 0) // 100,
                            'rating': p.get('rating', 0),
                            'feedbacks': p.get('feedbacks', 0),
                            'url': f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
                        }
                return None
        except Exception as e:
            print(f"[wb] error: {e}")
            return None

# ==================== МОДУЛЬ АНАЛИЗА ГОЛОСА ====================
async def download_voice_file(url: str) -> Optional[str]:
    """Скачивает голосовое сообщение во временный файл"""
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status == 200:
                fd, path = tempfile.mkstemp(suffix='.ogg')
                async with aiofiles.open(path, 'wb') as f:
                    await f.write(await resp.read())
                os.close(fd)
                return path
            return None

async def recognize_speech_vk(file_path: str) -> Optional[str]:
    """Распознавание через VK Cloud Speech (если есть ключ)"""
    if not VK_API_KEY:
        return None
    # Здесь должна быть интеграция с VK Cloud API
    # Для простоты вернём None (заглушка)
    return None

async def recognize_speech_openai(file_path: str) -> Optional[str]:
    """Распознавание через OpenAI Whisper (если есть ключ)"""
    if not OPENAI_API_KEY:
        return None
    # Используем OpenAI Audio API
    from openai import AsyncOpenAI
    client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    try:
        with open(file_path, 'rb') as f:
            transcript = await client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
                response_format="text"
            )
        return transcript
    except Exception as e:
        print(f"[whisper] error: {e}")
        return None

async def analyze_health_from_text(text: str) -> Dict:
    """
    Анализирует текст голосового сообщения и извлекает параметры здоровья.
    Использует простые регулярные выражения (без OpenAI) для демонстрации.
    """
    # Простейший парсинг (можно заменить на LLM)
    text_low = text.lower()
    health = {
        'energy': None,
        'sleep': None,
        'mood': None,
        'anxiety': None,
        'stress': None,
        'libido': None,
        'symptoms': [],
        'supplements': [],
        'lifestyle': []
    }
    # Энергия
    if 'энерги' in text_low or 'бодр' in text_low:
        health['energy'] = 7  # по умолчанию
        if 'мало энергии' in text_low or 'устал' in text_low:
            health['energy'] = 3
    # Сон
    if 'спал' in text_low:
        health['sleep'] = 6
        if 'плохо спал' in text_low or 'бессонниц' in text_low:
            health['sleep'] = 3
    # Настроение
    if 'хорош' in text_low or 'отличн' in text_low:
        health['mood'] = 8
    elif 'плох' in text_low or 'уныние' in text_low:
        health['mood'] = 3
    # Стресс
    if 'стресс' in text_low or 'нерв' in text_low:
        health['stress'] = 7
    # Тревога
    if 'тревог' in text_low or 'волн' in text_low:
        health['anxiety'] = 6
    # Либидо
    if 'либидо' in text_low or 'секс' in text_low:
        health['libido'] = 5
    return health

async def process_voice_message(voice_url: str) -> Dict:
    """Полный цикл обработки голосового сообщения"""
    # Скачиваем
    file_path = await download_voice_file(voice_url)
    if not file_path:
        return {'error': 'Не удалось скачать аудио'}
    # Распознаём (сначала VK, потом OpenAI)
    text = await recognize_speech_vk(file_path)
    if not text:
        text = await recognize_speech_openai(file_path)
    if not text:
        # Если распознавание не работает, возвращаем ошибку
        os.unlink(file_path)
        return {'error': 'Не удалось распознать речь, проверьте API ключи'}
    # Анализируем
    health = await analyze_health_from_text(text)
    health['original_text'] = text
    os.unlink(file_path)
    return health

# ==================== СОЦИАЛЬНЫЙ ГРАФ И ПРОГНОЗЫ ====================
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
        return {'prediction': 'Недостаточно данных', 'advice': 'Продолжайте общаться и фиксировать взаимодействия'}
    # Простой тренд
    agg_start, agg_end = rows[0][0], rows[-1][0]
    pos_start, pos_end = rows[0][1], rows[-1][1]
    if agg_end < agg_start and pos_end > pos_start:
        return {'prediction': 'Отношения улучшаются', 'advice': 'Отлично, продолжайте в том же духе!', 'confidence': 0.7}
    elif agg_end > agg_start and pos_end < pos_start:
        return {'prediction': 'Отношения ухудшаются', 'advice': 'Попробуйте изменить тактику общения', 'confidence': 0.65}
    else:
        return {'prediction': 'Стабильно', 'advice': 'Обратите внимание на мелочи, они важны', 'confidence': 0.6}

# ==================== ГЕНЕРАЦИЯ МЕНЮ ====================
async def generate_daily_menu(user_id: int, health: Dict) -> str:
    """Генерирует персонализированное меню БАД на основе здоровья"""
    # Базовый набор для всех
    base = [
        "🌅 *Утро (натощак)*: MAXFIT Collagen 5800 мг (коллаген, гиалуронка, C)",
        "🌞 *День (после еды)*: Омега-3-6-9 (Aksu vital) – 2 капсулы",
        "🌙 *Вечер*: Синбиотик Будь здоров! (10 штаммов) – 2 капсулы"
    ]
    extra = []
    # Энергия
    if health.get('energy', 5) < 5:
        extra.append("⚡ *Добавка для энергии*: Maxler Energy and Focus (утро, 2 капсулы)")
    # Сон
    if health.get('sleep', 5) < 5:
        extra.append("💤 *Для сна*: Магний + B6 (ZMA) – 3 капсулы вечером")
    # Стресс/тревога
    if health.get('anxiety', 5) > 6 or health.get('stress', 5) > 6:
        extra.append("🍃 *Антистресс*: Ашваганда (KSM-66) – 1 капсула вечером")
    # Либидо
    if health.get('libido', 5) is not None and health['libido'] < 5:
        extra.append("❤️ *Для либидо*: VPLab Tribulus + Zinc – 2 капсулы днём")
    # Память
    extra.append("🧠 *Ноотроп*: Ноотроп Память (ВИС) – 2 капсулы утром (для концентрации)")
    # Собираем
    menu = "\n".join(base + extra)
    menu += "\n\n💧 *Важно*: пейте не менее 2 л воды в день!"
    return menu

# ==================== ОСНОВНОЙ ВЕБХУК ====================
app = FastAPI()

async def handle_update(update: Dict):
    """Обработка входящего обновления от MAX"""
    print(f"[update] {json.dumps(update, ensure_ascii=False)[:500]}")
    # Извлекаем chat_id и текст
    message = update.get('message')
    if not message:
        return
    chat_id = message.get('chat', {}).get('id')
    if not chat_id:
        return
    user_id = chat_id
    # Текст команды
    text = message.get('text', '')
    # Голосовое вложение
    voice = message.get('attachments', {}).get('voice')
    
    # Обновляем активность пользователя
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO users (user_id, last_activity) VALUES (?, ?)",
              (user_id, datetime.now()))
    conn.commit()
    conn.close()
    
    # Обработка команд
    if text.startswith('/'):
        cmd = text.split()[0].lower()
        if cmd == '/start':
            await send_message(chat_id,
                "🧬 *Formula 100 AI*\n\nПривет! Я твой персональный AI-ассистент.\n"
                "Отправь мне голосовое сообщение – я проанализирую твоё здоровье.\n\n"
                "Команды:\n"
                "/wb <артикул> – цены на WB\n"
                "/daily – моё меню на сегодня\n"
                "/social <имя> <роль> <агрессия> <интеллект> <позитив> <событие> – сохранить взаимодействие\n"
                "/predict <имя> – прогноз отношений\n"
                "/help – помощь")
        elif cmd == '/help':
            await send_message(chat_id,
                "📖 *Помощь*\n"
                "/start – приветствие\n"
                "/wb 12345678 – получить данные о товаре WB\n"
                "/daily – персональное меню БАД\n"
                "/social – сохранить социальное взаимодействие\n"
                "/predict – прогноз развития отношений\n"
                "Отправь голосовое – анализ здоровья")
        elif cmd == '/wb':
            parts = text.split()
            if len(parts) < 2:
                await send_message(chat_id, "❌ Укажите артикул: /wb 12345678")
            else:
                article = parts[1]
                await send_message(chat_id, f"🔍 Ищу товар {article}...")
                prod = await fetch_wb_product(article)
                if prod:
                    msg = (f"📦 *{prod['name']}*\n"
                           f"🏷 Бренд: {prod['brand']}\n"
                           f"💰 Цена: {prod['price']} руб.\n"
                           f"⭐ Рейтинг: {prod['rating']}\n"
                           f"📝 Отзывов: {prod['feedbacks']}\n"
                           f"🔗 [Ссылка]({prod['url']})")
                    await send_message(chat_id, msg)
                else:
                    await send_message(chat_id, "❌ Товар не найден")
        elif cmd == '/daily':
            # Берём последние данные здоровья из БД или заглушку
            health = {'energy': 5, 'sleep': 5, 'anxiety': 5, 'stress': 5, 'libido': 5}
            menu = await generate_daily_menu(user_id, health)
            await send_message(chat_id, menu)
        elif cmd == '/social':
            # Формат: /social Иван коллега 3 8 7 Помог с проектом
            parts = text.split(maxsplit=6)
            if len(parts) < 7:
                await send_message(chat_id, "❌ Формат: /social <имя> <роль> <агрессия> <интеллект> <позитив> <событие>")
            else:
                _, name, role, agg_str, intel_str, pos_str, event = parts
                try:
                    agg = int(agg_str)
                    intel = int(intel_str)
                    pos = int(pos_str)
                except:
                    await send_message(chat_id, "❌ Агрессия, интеллект, позитив должны быть числами 1-10")
                    return
                await save_interaction(user_id, name, role, agg, intel, pos, event)
                await send_message(chat_id, f"✅ Взаимодействие с {name} сохранено")
        elif cmd == '/predict':
            parts = text.split()
            if len(parts) < 2:
                await send_message(chat_id, "❌ Укажите имя: /predict Иван")
            else:
                name = parts[1]
                pred = await predict_relationship(user_id, name)
                await send_message(chat_id,
                    f"🔮 *Прогноз отношений с {name}*\n"
                    f"📈 {pred['prediction']}\n"
                    f"💡 {pred['advice']}\n"
                    f"🎯 Уверенность: {pred.get('confidence', 0.5)*100:.0f}%")
        else:
            await send_message(chat_id, "Неизвестная команда. /help")
    elif voice:
        # Обработка голосового сообщения
        await send_message(chat_id, "🎤 Анализирую ваше голосовое сообщение, подождите...")
        voice_url = voice.get('url')
        if voice_url:
            health = await process_voice_message(voice_url)
            if 'error' in health:
                await send_message(chat_id, f"❌ {health['error']}")
            else:
                # Сохраняем health_data в БД
                conn = sqlite3.connect(DB_PATH)
                c = conn.cursor()
                c.execute("UPDATE users SET health_data = ? WHERE user_id = ?",
                          (json.dumps(health, ensure_ascii=False), user_id))
                conn.commit()
                conn.close()
                # Формируем ответ
                response = "📊 *Результаты анализа здоровья*\n\n"
                response += f"📝 Распознанный текст: *{health.get('original_text', '')}*\n\n"
                response += "Показатели:\n"
                for k in ['energy','sleep','mood','anxiety','stress','libido']:
                    v = health.get(k)
                    if v is not None:
                        response += f"• {k.capitalize()}: {v}/10\n"
                if health.get('symptoms'):
                    response += f"\n⚠️ Симптомы: {', '.join(health['symptoms'])}\n"
                await send_message(chat_id, response)
                # Сразу выдаём меню
                menu = await generate_daily_menu(user_id, health)
                await send_message(chat_id, menu)
        else:
            await send_message(chat_id, "❌ Не удалось получить ссылку на аудио")
    else:
        # Просто эхо
        await send_message(chat_id, f"Вы написали: {text}")

@app.post(WEBHOOK_PATH)
async def webhook(request: Request, background_tasks: BackgroundTasks):
    try:
        update = await request.json()
    except:
        return Response(status_code=400)
    # Обрабатываем в фоне, чтобы быстро ответить MAX
    background_tasks.add_task(handle_update, update)
    return JSONResponse(content={"status": "ok"})

@app.get("/")
async def root():
    return {"status": "alive", "bot": BOT_USERNAME}

# ==================== УСТАНОВКА ВЕБХУКА ====================
async def set_webhook():
    """Устанавливает вебхук для бота (вызывается один раз при запуске)"""
    # Получаем публичный URL из переменной окружения (Bothost даёт домен)
    # Если не задан, пробуем определить из request? В Bothost обычно передаётся через PUBLIC_URL
    public_url = os.getenv("PUBLIC_URL") or os.getenv("WEBHOOK_URL")
    if not public_url:
        # Для теста можно задать вручную, но лучше через Env
        print("⚠️ PUBLIC_URL не задан, вебхук не будет установлен")
        return
    webhook_url = f"{public_url.rstrip('/')}{WEBHOOK_PATH}"
    url = f"{MAX_API_URL}/subscriptions"
    payload = {"url": webhook_url, "update_types": ["message_created"]}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status == 200:
                print(f"✅ Вебхук установлен: {webhook_url}")
            else:
                text = await resp.text()
                print(f"❌ Ошибка установки вебхука: {resp.status} - {text}")

# ==================== ЗАПУСК ====================
@asynccontextmanager
async def lifespan(app: FastAPI):
    # При старте устанавливаем вебхук
    await set_webhook()
    yield

app.router.lifespan_context = lifespan

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)

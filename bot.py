# bot.py
import asyncio
import logging
import os
import tempfile
from datetime import datetime
from typing import Dict, Any

from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated, Voice
from aiohttp import ClientSession
from aiofiles import open as aio_open
import json

from wb_integration import fetch_product_by_api, fetch_product_by_parsing, update_product_prices
from voice_analysis import process_voice_message
from social_graph import save_social_interaction, predict_relationship_evolution, generate_daily_menu

# --- НАСТРОЙКИ ---
TOKEN = "ВАШ_ТОКЕН_БОТА"
WB_TOKEN = "ВАШ_API_ТОКЕН_WB"  # Если есть, иначе будет использован парсинг

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- 1. ОБРАБОТЧИК СОБЫТИЙ ---
@dp.bot_started()
async def on_bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="🧬 *Formula 100 AI*\n\nПривет! Я твой персональный AI-ассистент для здоровья.\n\n"
             "Я умею:\n"
             "🔹 Анализировать твои голосовые сообщения\n"
             "🔹 Давать рекомендации по БАДам\n"
             "🔹 Показывать актуальные цены на Wildberries\n"
             "🔹 Прогнозировать развитие отношений\n\n"
             "Отправь мне голосовое сообщение, и я проанализирую твое здоровье!\n"
             "Используй /help для списка команд.",
        parse_mode="markdown"
    )

# --- 2. ОБРАБОТЧИКИ КОМАНД ---
@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    await event.message.answer(
        "🧬 Добро пожаловать в Formula 100 AI!\n\n"
        "Я твой персональный AI-ассистент для здоровья.\n"
        "Отправь мне голосовое сообщение, и я проанализирую твое самочувствие."
    )

@dp.message_created(Command('help'))
async def cmd_help(event: MessageCreated):
    await event.message.answer(
        "📖 *Список команд:*\n"
        "/start — Начать работу\n"
        "/help — Справка\n"
        "/wb <артикул> — Получить актуальную информацию о товаре на Wildberries\n"
        "/daily — Сформировать персональное меню на день\n\n"
        "Также я могу анализировать голосовые сообщения. Просто отправь их мне!",
        parse_mode="markdown"
    )

# --- 3. РАБОТА С WILDBERRIES ---
@dp.message_created(Command('wb'))
async def cmd_wb(event: MessageCreated):
    parts = event.message.body.text.split(' ')
    if len(parts) < 2:
        await event.message.answer("❌ Укажите артикул товара после команды /wb")
        return
    
    article = parts[1]
    await event.message.answer(f"🔍 Ищу информацию о товаре {article}...")
    
    # Сначала пробуем получить данные через API (если есть токен)
    if WB_TOKEN:
        product_data = await fetch_product_by_api(article, WB_TOKEN)
    else:
        product_data = None
    
    # Если API не сработал или токена нет, используем парсинг
    if not product_data:
        product_data = await fetch_product_by_parsing(article)
    
    if product_data:
        response_text = (
            f"📦 *{product_data.get('name', 'Информация не найдена')}*\n"
            f"🏷 Бренд: {product_data.get('brand', 'Не указан')}\n"
            f"💰 Цена: {product_data.get('price', 'Не указана')} руб.\n"
            f"⭐️ Рейтинг: {product_data.get('rating', 'Нет данных')}\n"
            f"📝 Отзывов: {product_data.get('feedbacks', 'Нет данных')}\n"
            f"🔗 [Ссылка на товар]({product_data.get('url', '#')})"
        )
        await event.message.answer(response_text, parse_mode="markdown")
    else:
        await event.message.answer("❌ Не удалось получить информацию о товаре. Проверьте артикул.")

# --- 4. ПЕРСОНАЛЬНОЕ МЕНЮ НА ДЕНЬ ---
@dp.message_created(Command('daily'))
async def cmd_daily(event: MessageCreated):
    # Здесь должна быть логика получения актуальных данных о здоровье пользователя
    # Для демонстрации используем заглушку
    health_data = {
        'energy': 6,
        'sleep': 4,
        'stress': 7,
        'mood': 5,
        'anxiety': 5,
        'libido': None
    }
    
    menu = await generate_daily_menu(event.message.body.chat_id, health_data)
    await event.message.answer(menu, parse_mode="markdown")

# --- 5. АНАЛИЗ ГОЛОСОВЫХ СООБЩЕНИЙ ---
@dp.message_created()
async def voice_message_handler(event: MessageCreated):
    """Обработчик голосовых сообщений."""
    voice_attachment = event.message.body.get('attachments', {}).get('voice')
    if not voice_attachment:
        return
    
    await event.message.answer("🎤 Анализирую ваше голосовое сообщение...")
    
    # Сохраняем голосовое сообщение во временный файл
    voice_url = voice_attachment.get('url')
    if not voice_url:
        await event.message.answer("❌ Не удалось получить аудиофайл.")
        return
    
    temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.ogg')
    try:
        async with ClientSession() as session:
            async with session.get(voice_url) as resp:
                if resp.status == 200:
                    async with aio_open(temp_file.name, 'wb') as f:
                        await f.write(await resp.read())
                else:
                    await event.message.answer("❌ Не удалось загрузить аудиофайл.")
                    return
    except Exception as e:
        await event.message.answer(f"❌ Ошибка при загрузке аудио: {str(e)}")
        return
    
    # Анализируем голосовое сообщение
    health_analysis = await process_voice_message(temp_file.name)
    os.unlink(temp_file.name)  # Удаляем временный файл
    
    if 'error' in health_analysis:
        await event.message.answer(f"❌ {health_analysis['error']}")
        return
    
    # Формируем ответ
    response = "📊 *Результаты анализа:*\n\n"
    response += f"📝 Распознанный текст: *{health_analysis.get('original_text', 'Не распознан')}*\n\n"
    response += "*Показатели здоровья:*\n"
    
    metrics = ['energy', 'sleep', 'mood', 'anxiety', 'libido', 'stress']
    for metric in metrics:
        value = health_analysis.get(metric)
        if value is not None:
            response += f"• {metric.capitalize()}: {value}/10\n"
    
    if health_analysis.get('symptoms'):
        response += f"\n⚠️ Симптомы: {health_analysis['symptoms']}\n"
    
    if health_analysis.get('supplements'):
        response += f"💊 БАДы: {health_analysis['supplements']}\n"
    
    await event.message.answer(response, parse_mode="markdown")
    
    # Формируем персональное меню на основе анализа
    menu = await generate_daily_menu(event.message.body.chat_id, health_analysis)
    await event.message.answer(menu, parse_mode="markdown")

# --- 6. ФОНОВЫЕ ЗАДАЧИ ---
async def background_tasks():
    """Фоновые задачи для бота."""
    while True:
        # Обновление цен на Wildberries каждый час
        await update_product_prices()
        await asyncio.sleep(3600)  # 1 час

# --- 7. ЗАПУСК БОТА ---
async def main():
    # Запуск бота с обработкой нескольких типов событий
    # Используем простой polling для получения обновлений
    # Вы можете переключиться на вебхук по необходимости
    logging.basicConfig(level=logging.INFO)
    
    # Запускаем фоновые задачи
    asyncio.create_task(background_tasks())
    
    print("🚀 Бот запущен и ожидает сообщений...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())

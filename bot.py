#!/usr/bin/env python3
import asyncio
import aiohttp
import json
import os
import sys

# === НАСТРОЙКИ ===
TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("❌ КРИТИЧЕСКАЯ ОШИБКА: переменная окружения MAX_TOKEN не установлена", file=sys.stderr)
    sys.exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}
print("✅ Токен загружен, заголовок установлен", flush=True)

# === ФУНКЦИИ API ===
async def get_updates(offset=None):
    """Запрос новых обновлений (long polling)"""
    url = f"{BASE_URL}/updates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("updates", [])
            else:
                text = await resp.text()
                print(f"⚠️ Ошибка get_updates: {resp.status} - {text}", flush=True)
                return []

async def send_message(chat_id, text):
    """Отправить текстовое сообщение"""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                text_err = await resp.text()
                print(f"⚠️ Ошибка send_message: {resp.status} - {text_err}", flush=True)

# === ОБРАБОТЧИК ===
async def handle_update(update):
    """Разбор входящего update (сообщения)"""
    # Структура сообщения в MAX может быть разной, делаем безопасный доступ
    message = update.get("message")
    if not message or not isinstance(message, dict):
        return
    chat = message.get("chat")
    if not chat or not isinstance(chat, dict):
        return
    chat_id = chat.get("id")
    if not chat_id:
        return
    text = message.get("text", "")
    if not text:
        # можно обработать голосовые, но для старта игнорируем
        return

    print(f"📩 Получено сообщение от {chat_id}: {text}", flush=True)

    if text == "/start":
        await send_message(chat_id, "Привет! Я Формула жизни. Бот работает!")
    elif text == "/help":
        await send_message(chat_id, "Доступные команды: /start, /help")
    else:
        await send_message(chat_id, f"Вы написали: {text}")

# === ГЛАВНЫЙ ЦИКЛ ===
async def main():
    print("🚀 Бот запущен, начинаю polling...", flush=True)
    last_update_id = 0
    while True:
        updates = await get_updates(offset=last_update_id + 1 if last_update_id else None)
        for upd in updates:
            await handle_update(upd)
            if "update_id" in upd:
                last_update_id = upd["update_id"]
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

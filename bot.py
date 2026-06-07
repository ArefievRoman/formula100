import asyncio
import aiohttp
import os
import json
import sys

TOKEN = os.getenv(MAX_TOKEN)
if not TOKEN:
    print("❌ Ошибка: переменная окружения MAX_TOKEN не установлена")
    sys.exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

async def get_updates(offset=None):
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
                print(f"Ошибка получения обновлений: {resp.status} {text}")
                return []

async def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                text_err = await resp.text()
                print(f"Ошибка отправки: {resp.status} {text_err}")

async def handle_update(update):
    # Выведем структуру в лог для отладки (один раз)
    print(f"DEBUG update: {json.dumps(update, ensure_ascii=False, indent=2)}")
    
    # Попробуем извлечь chat_id и текст
    if "message" in update:
        msg = update["message"]
        # Варианты: msg["chat"]["id"] или msg["from"]["id"] или msg["user"]["id"]
        chat_id = None
        if "chat" in msg and "id" in msg["chat"]:
            chat_id = msg["chat"]["id"]
        elif "from" in msg and "id" in msg["from"]:
            chat_id = msg["from"]["id"]
        elif "user" in msg and "id" in msg["user"]:
            chat_id = msg["user"]["id"]
        else:
            print("Не удалось найти chat_id в update")
            return
        
        text = msg.get("text", "")
        
        if text == "/start":
            await send_message(chat_id, "Привет! Я Формула жизни. Бот работает.")
        elif text == "/help":
            await send_message(chat_id, "Команды: /start, /help")
        elif text:
            await send_message(chat_id, f"Вы написали: {text}")

async def main():
    print("🚀 Бот запущен и ожидает сообщений...")
    last_update_id = None
    while True:
        updates = await get_updates(offset=last_update_id)
        for update in updates:
            await handle_update(update)
            if "update_id" in update:
                last_update_id = update["update_id"] + 1
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

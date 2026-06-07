import asyncio
import aiohttp
import os

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("❌ Ошибка: переменная окружения MAX_TOKEN не установлена")
    exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

async def get_updates(offset=None):
    """Получить новые сообщения"""
    url = f"{BASE_URL}/updates"
    params = {"timeout": 30, "offset": offset} if offset else {"timeout": 30}
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("updates", [])
            else:
                text = await resp.text()
                print(f"Ошибка при получении обновлений: {resp.status} - {text}")
                return []

async def send_message(chat_id, text):
    """Отправить сообщение пользователю"""
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                text = await resp.text()
                print(f"Ошибка отправки сообщения: {resp.status} - {text}")

async def handle_update(update):
    """Обработать одно обновление"""
    # Если есть сообщение
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = msg.get("text", "")
        
        if text == "/start":
            await send_message(chat_id, "Привет! Я Формула жизни. Бот работает.")
        elif text == "/help":
            await send_message(chat_id, "Команды: /start, /help")
        else:
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
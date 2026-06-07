import sys
import os
import asyncio
import aiohttp
import json
import sqlite3
from datetime import datetime

# Принудительный вывод без буферизации
sys.stdout = os.fdopen(sys.stdout.fileno(), 'w', buffering=1)
sys.stderr = os.fdopen(sys.stderr.fileno(), 'w', buffering=1)

print("START: Бот начал работу", flush=True)

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("ERROR: MAX_TOKEN not set", flush=True)
    sys.exit(1)

print(f"Token received, len = {len(TOKEN)}", flush=True)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

# ========== БАЗА ДАННЫХ ==========
def init_db():
    conn = sqlite3.connect("formula100.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, registered_at TIMESTAMP, goals TEXT)")
    conn.commit()
    conn.close()
    print("DB init ok", flush=True)

init_db()

# ========== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==========
async def send_message(chat_id: int, text: str):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                txt = await resp.text()
                print(f"Send error {resp.status}: {txt}", flush=True)

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
                txt = await resp.text()
                print(f"Updates error {resp.status}: {txt}", flush=True)
                return []

# ========== ОБРАБОТЧИК СООБЩЕНИЙ ==========
async def handle_message(chat_id, text):
    if text == "/start":
        await send_message(chat_id, "🧬 *Formula 100 AI*\n\nПривет! Я бот для подбора БАД.\nИспользуй /help для списка команд.")
    elif text == "/help":
        await send_message(chat_id, "📖 Команды:\n/questionnaire – анкета\n/recommend – рекомендация\n/help – справка")
    elif text == "/questionnaire":
        await send_message(chat_id, "Функция анкетирования в разработке. Скоро будет!")
    elif text == "/recommend":
        await send_message(chat_id, "Рекомендация: коллаген, омега-3, мультивитамины, пиперин. Точный подбор после анкеты.")
    else:
        await send_message(chat_id, "Я вас не понял. Напишите /help")

# ========== ГЛАВНЫЙ ЦИКЛ ==========
async def main():
    print("Entering main loop", flush=True)
    last_update_id = 0
    while True:
        updates = await get_updates(offset=last_update_id + 1 if last_update_id else None)
        for upd in updates:
            # Проверяем структуру: у MAX обновление может содержать поле "message"
            msg = upd.get("message")
            if msg and isinstance(msg, dict):
                # Поле "chat" есть, а внутри "id"
                chat = msg.get("chat")
                if chat and "id" in chat:
                    chat_id = chat["id"]
                    text = msg.get("text", "")
                    if text:
                        await handle_message(chat_id, text)
                else:
                    print("No chat id in update", flush=True)
            else:
                print(f"Update without message: {upd}", flush=True)
            if "update_id" in upd:
                last_update_id = upd["update_id"]
        await asyncio.sleep(1)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Бот остановлен", flush=True)
    except Exception as e:
        print(f"Unhandled: {e}", flush=True)
        import traceback
        traceback.print_exc()

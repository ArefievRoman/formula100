#!/usr/bin/env python3
import asyncio
import aiohttp
import os
import json
import sys

# Форсированный вывод
sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("❌ ОШИБКА: MAX_TOKEN не установлен")
    sys.exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

def extract_chat_id(obj):
    """Рекурсивно ищет chat_id в любом месте update"""
    if isinstance(obj, dict):
        if 'chat' in obj and isinstance(obj['chat'], dict) and 'id' in obj['chat']:
            return obj['chat']['id']
        if 'from' in obj and isinstance(obj['from'], dict) and 'id' in obj['from']:
            return obj['from']['id']
        for v in obj.values():
            res = extract_chat_id(v)
            if res:
                return res
    elif isinstance(obj, list):
        for item in obj:
            res = extract_chat_id(item)
            if res:
                return res
    return None

async def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                print(f"Ошибка отправки: {resp.status}")

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
                print(f"Ошибка get_updates: {resp.status}")
                return []

async def main():
    print("🚀 Бот запущен, ожидаем сообщения...")
    last_update_id = 0
    while True:
        updates = await get_updates(offset=last_update_id+1 if last_update_id else None)
        for upd in updates:
            # Печатаем полный JSON для отладки
            print(f"RAW UPDATE: {json.dumps(upd, ensure_ascii=False)}")
            # Извлекаем chat_id
            chat_id = extract_chat_id(upd)
            if not chat_id:
                print("Не удалось извлечь chat_id")
                continue
            # Извлекаем текст сообщения
            text = None
            if 'message' in upd and isinstance(upd['message'], dict):
                text = upd['message'].get('text')
            if text:
                if text == '/start':
                    await send_message(chat_id, "Привет! Бот работает. Отправь любое сообщение.")
                else:
                    await send_message(chat_id, f"Вы сказали: {text}")
            else:
                print(f"Нет текста в update, но есть другие поля")
            # Обновляем offset
            if 'update_id' in upd:
                last_update_id = upd['update_id']
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

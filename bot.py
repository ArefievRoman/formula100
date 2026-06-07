#!/usr/bin/env python3
import asyncio
import aiohttp
import os
import json
import sys

sys.stdout.reconfigure(line_buffering=True)
sys.stderr.reconfigure(line_buffering=True)

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("❌ MAX_TOKEN not set")
    sys.exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

async def delete_webhook():
    url = f"{BASE_URL}/deleteWebhook"
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS) as resp:
            print(f"deleteWebhook status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"deleteWebhook response: {data}")

async def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                print(f"sendMessage error: {resp.status}")

async def get_updates(offset=None):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            if resp.status == 200:
                data = await resp.json()
                return data.get("updates", [])
            else:
                print(f"getUpdates error: {resp.status}")
                return []

async def main():
    print("🚀 Бот запущен, удаляем вебхук...")
    await delete_webhook()
    print("🚀 Ожидаем сообщения...")
    last_update_id = 0
    while True:
        updates = await get_updates(offset=last_update_id+1 if last_update_id else None)
        for upd in updates:
            print(f"RAW: {json.dumps(upd, ensure_ascii=False)}")
            # Ищем chat_id
            chat_id = None
            if 'message' in upd:
                msg = upd['message']
                if 'chat' in msg and 'id' in msg['chat']:
                    chat_id = msg['chat']['id']
                elif 'from' in msg and 'id' in msg['from']:
                    chat_id = msg['from']['id']
            if not chat_id:
                print("No chat_id")
                continue
            text = upd.get('message', {}).get('text', '')
            if text:
                await send_message(chat_id, f"Эхо: {text}")
            if 'update_id' in upd:
                last_update_id = upd['update_id']
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

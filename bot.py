import asyncio
import aiohttp
import os
import json

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("MAX_TOKEN not set")
    exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

async def get_updates(offset=None):
    url = f"{BASE_URL}/updates"
    params = {"timeout": 30}
    if offset:
        params["offset"] = offset
    async with aiohttp.ClientSession() as session:
        async with session.get(url, headers=HEADERS, params=params) as resp:
            print(f"get_updates status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"get_updates data: {json.dumps(data, ensure_ascii=False)}")
                return data.get("updates", [])
            else:
                text = await resp.text()
                print(f"Error: {text}")
                return []

async def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                text_err = await resp.text()
                print(f"Send error: {resp.status} {text_err}")

async def main():
    print("Starting bot")
    last_update_id = 0
    while True:
        updates = await get_updates(offset=last_update_id+1 if last_update_id else None)
        for update in updates:
            print(f"Update: {json.dumps(update, ensure_ascii=False)}")
            # Ищем chat_id в любом месте
            chat_id = None
            if 'message' in update:
                msg = update['message']
                if 'chat' in msg and 'id' in msg['chat']:
                    chat_id = msg['chat']['id']
                elif 'from' in msg and 'id' in msg['from']:
                    chat_id = msg['from']['id']
            if chat_id:
                text = update.get('message', {}).get('text', '')
                if text == '/start':
                    await send_message(chat_id, "Привет! Бот работает.")
                else:
                    await send_message(chat_id, f"Эхо: {text}")
            if 'update_id' in update:
                last_update_id = update['update_id']
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

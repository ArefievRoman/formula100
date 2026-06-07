#!/usr/bin/env python3
import sys
import os
import asyncio
import aiohttp
import json
import sqlite3
from datetime import datetime

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("ERROR: MAX_TOKEN not set")
    sys.exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

async def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                print(f"Send error: {resp.status}")

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
                print(f"Get updates error: {resp.status}")
                return []

async def handle_message(chat_id, text):
    if text == "/start":
        await send_message(chat_id, "Привет! Я Formula 100 AI. Бот работает.")
    else:
        await send_message(chat_id, "Напишите /start")

async def main():
    print("START: Bot started")
    # init db
    conn = sqlite3.connect("data.db")
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    print("DB init ok")
    last_update_id = 0
    while True:
        updates = await get_updates(offset=last_update_id+1 if last_update_id else None)
        for upd in updates:
            # диагностика
            print(f"DEBUG update: {json.dumps(upd, ensure_ascii=False)}")
            # извлечение chat_id
            chat_id = None
            if "message" in upd:
                msg = upd["message"]
                if "chat" in msg and "id" in msg["chat"]:
                    chat_id = msg["chat"]["id"]
                elif "from" in msg and "id" in msg["from"]:
                    # иногда в MAX чат = from
                    chat_id = msg["from"]["id"]
            if not chat_id:
                print("No chat id in update")
                continue
            text = upd.get("message", {}).get("text", "")
            if text:
                await handle_message(chat_id, text)
            if "update_id" in upd:
                last_update_id = upd["update_id"]
        await asyncio.sleep(1)

if __name__ == "__main__":
    asyncio.run(main())

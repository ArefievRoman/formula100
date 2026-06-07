import os
import aiohttp
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    raise RuntimeError("MAX_TOKEN not set")

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: устанавливаем вебхук
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        async with aiohttp.ClientSession() as session:
            set_url = f"{BASE_URL}/setWebhook"
            payload = {"url": webhook_url}
            async with session.post(set_url, headers=HEADERS, json=payload) as resp:
                print(f"setWebhook status: {resp.status}")
                if resp.status == 200:
                    print("Webhook set successfully")
                else:
                    print(await resp.text())
    else:
        print("WEBHOOK_URL not set, webhook not configured")
    yield
    # Shutdown (опционально)

app = FastAPI(lifespan=lifespan)

async def send_message(chat_id: int, text: str):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                print(f"Send error {resp.status}: {await resp.text()}")

@app.post("/")
async def webhook(request: Request):
    update = await request.json()
    print(f"Received update: {update}")
    # Извлечение chat_id и текста (структура может различаться, сделаем универсально)
    try:
        msg = update.get("message")
        if msg:
            chat_id = msg.get("chat", {}).get("id") or msg.get("from", {}).get("id")
            text = msg.get("text", "")
            if chat_id:
                if text == "/start":
                    await send_message(chat_id, "Привет! Бот работает через вебхук.")
                else:
                    await send_message(chat_id, f"Вы написали: {text}")
    except Exception as e:
        print(f"Error processing update: {e}")
    return Response(status_code=200)

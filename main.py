from fastapi import FastAPI, Request, Response
import uvicorn
import os
import aiohttp
from contextlib import asynccontextmanager

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    raise RuntimeError("MAX_TOKEN not set")

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

async def send_message(chat_id: int, text: str):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                print(f"Send error: {resp.status}")

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    webhook_url = os.getenv("WEBHOOK_URL")
    if webhook_url:
        set_url = f"{BASE_URL}/setWebhook"
        async with aiohttp.ClientSession() as session:
            async with session.post(set_url, headers=HEADERS, json={"url": webhook_url}) as resp:
                print(f"setWebhook status: {resp.status}")
                if resp.status != 200:
                    print(await resp.text())
    else:
        print("WEBHOOK_URL not set, webhook not configured")
    yield
    # Shutdown (опционально)

app = FastAPI(lifespan=lifespan)

@app.post("/")
async def webhook(request: Request):
    update = await request.json()
    print(f"Update: {update}")
    # Простейшая обработка
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "")
        if chat_id:
            if text == "/start":
                await send_message(chat_id, "Привет! Бот работает через вебхук.")
            else:
                await send_message(chat_id, f"Вы написали: {text}")
    return Response(status_code=200)

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

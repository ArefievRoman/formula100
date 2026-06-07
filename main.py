from fastapi import FastAPI, Request, Response
import uvicorn
import os
import aiohttp
import json

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    raise RuntimeError("MAX_TOKEN not set")

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

app = FastAPI()

async def send_message(chat_id: int, text: str):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                print(f"Send error: {resp.status}")

@app.post("/")
async def webhook(request: Request):
    update = await request.json()
    print(f"Update received: {json.dumps(update, ensure_ascii=False)}")
    if "message" in update:
        msg = update["message"]
        chat_id = msg.get("chat", {}).get("id")
        text = msg.get("text", "")
        if chat_id:
            if text == "/start":
                await send_message(chat_id, "Привет! Бот работает через вебхук.")
            else:
                await send_message(chat_id, f"Вы сказали: {text}")
    return Response(status_code=200)

# Установка вебхука при старте (не on_event, а через lifespan)
@app.on_event("startup")
async def setup_webhook():
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        print("WEBHOOK_URL not set, webhook not set")
        return
    # Для Bothost URL обычно вида https://ваш_бот.bothost.ru/
    # Убедитесь, что этот URL доступен из интернета и заканчивается на '/'
    if not webhook_url.endswith('/'):
        webhook_url += '/'
    url = f"{BASE_URL}/setWebhook"
    payload = {"url": webhook_url}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            print(f"setWebhook status: {resp.status}")
            if resp.status == 200:
                print("Webhook set successfully")
            else:
                text = await resp.text()
                print(f"Failed: {text}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)

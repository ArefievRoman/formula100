import os
import logging
import aiohttp
from fastapi import FastAPI, Request, Response
import uvicorn

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    logging.error("MAX_TOKEN not set")
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
                logging.error(f"Send error {resp.status}: {await resp.text()}")
            else:
                logging.info(f"Sent to {chat_id}: {text[:50]}")

@app.post("/")
async def webhook(request: Request):
    try:
        update = await request.json()
        logging.info(f"Received update: {update}")
        if "message" in update:
            msg = update["message"]
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")
            if chat_id:
                if text == "/start":
                    await send_message(chat_id, "Привет! Бот работает через вебхук. Отправь любое сообщение.")
                else:
                    await send_message(chat_id, f"Вы написали: {text}")
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
    return Response(status_code=200)

@app.on_event("startup")
async def setup_webhook():
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        logging.warning("WEBHOOK_URL not set, skipping webhook setup")
        return
    url = f"{BASE_URL}/setWebhook"
    payload = {"url": webhook_url}
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=HEADERS, json=payload) as resp:
                if resp.status == 200:
                    logging.info("Webhook set successfully")
                else:
                    logging.error(f"setWebhook failed with {resp.status}: {await resp.text()}")
    except Exception as e:
        logging.error(f"Exception setting webhook: {e}")

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

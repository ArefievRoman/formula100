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

@app.post("/")
async def webhook(request: Request):
    try:
        update = await request.json()
        print(f"Webhook received: {json.dumps(update, ensure_ascii=False)}")
        # Обработка сообщения
        if "message" in update:
            msg = update["message"]
            chat_id = msg.get("chat", {}).get("id")
            text = msg.get("text", "")
            if chat_id:
                # Отправляем эхо
                url = f"{BASE_URL}/sendMessage"
                async with aiohttp.ClientSession() as session:
                    payload = {"chat_id": chat_id, "text": f"Вы сказали: {text}"}
                    async with session.post(url, headers=HEADERS, json=payload) as resp:
                        print(f"Send message status: {resp.status}")
    except Exception as e:
        print(f"Error: {e}")
    return Response(status_code=200)

@app.get("/")
async def root():
    return {"status": "ok", "message": "Bot webhook endpoint"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 3000))
    uvicorn.run(app, host="0.0.0.0", port=port)

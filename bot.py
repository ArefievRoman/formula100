import asyncio
import aiohttp
from aiohttp import web
import os
import json

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    raise Exception("MAX_TOKEN not set")

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

async def send_message(chat_id, text):
    url = f"{BASE_URL}/sendMessage"
    payload = {"chat_id": chat_id, "text": text}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            if resp.status != 200:
                print(f"Send error: {resp.status}")

async def handle_webhook(request):
    data = await request.json()
    print(f"Webhook received: {json.dumps(data, ensure_ascii=False)}")
    # Извлекаем chat_id и текст
    if 'message' in data:
        msg = data['message']
        chat_id = msg.get('chat', {}).get('id') or msg.get('from', {}).get('id')
        text = msg.get('text', '')
        if chat_id:
            await send_message(chat_id, f"Эхо: {text}")
    return web.Response(text="OK")

async def set_webhook(webhook_url):
    url = f"{BASE_URL}/setWebhook"
    payload = {"url": webhook_url}
    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=HEADERS, json=payload) as resp:
            print(f"setWebhook status: {resp.status}")
            if resp.status == 200:
                print(await resp.json())

async def main():
    # Получаем URL вебхука из переменной окружения (Bothost предоставляет)
    webhook_url = os.getenv("WEBHOOK_URL")
    if not webhook_url:
        print("WEBHOOK_URL not set, using default /webhook")
        webhook_url = "/webhook"  # относительный путь
    else:
        await set_webhook(webhook_url)

    app = web.Application()
    app.router.add_post("/webhook", handle_webhook)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "8080")))
    await site.start()
    print(f"Webhook server started on port {os.getenv('PORT', '8080')}")
    await asyncio.Event().wait()  # бесконечное ожидание

if __name__ == "__main__":
    asyncio.run(main())

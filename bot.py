import asyncio
import aiohttp
import os
import sys

sys.stdout.reconfigure(line_buffering=True)

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("❌ MAX_TOKEN не установлен")
    sys.exit(1)

BASE_URL = "https://botapi.max.ru"
HEADERS = {"Authorization": TOKEN}

async def test_api():
    async with aiohttp.ClientSession() as session:
        # Проверяем /getMe (или /me)
        async with session.get(f"{BASE_URL}/me", headers=HEADERS) as resp:
            print(f"GET /me status: {resp.status}")
            if resp.status == 200:
                data = await resp.json()
                print(f"Bot info: {data}")
            else:
                text = await resp.text()
                print(f"Error: {text}")

async def main():
    print("🚀 Тест API запущен")
    await test_api()
    # Не завершаемся, чтобы посмотреть логи
    await asyncio.sleep(10)

asyncio.run(main())

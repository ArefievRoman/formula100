import sys
import os

print("START: Бот начал работу", flush=True)
sys.stdout.flush()

TOKEN = os.getenv("MAX_TOKEN")
if not TOKEN:
    print("ERROR: MAX_TOKEN not set", flush=True)
    sys.exit(1)

print("Token received, len =", len(TOKEN), flush=True)

import asyncio
import aiohttp

print("Modules imported", flush=True)

async def main():
    print("Entering main loop", flush=True)
    while True:
        print("Tick", flush=True)
        await asyncio.sleep(10)

asyncio.run(main())

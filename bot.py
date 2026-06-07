import sys
import os

print("START: Бот начал работу", flush=True)
sys.stdout.flush()

TOKEN = "f9LHodD0cOIBqiz68b2fIVi8e3UZ4V9DZueBGWc_pxKgtGhxh8DLHbmX5iGofyZizBrG9GPiF9YacLbixLvQ"
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

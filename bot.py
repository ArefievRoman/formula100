import asyncio
import logging
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated

# Вставь свой токен (можно через переменную окружения, но для простоты пока так)
TOKEN = "f9LHodD0cOIBqiz68b2fIVi8e3UZ4V9DZueBGWc_pxKgtGhxh8DLHbmX5iGofyZizBrG9GPiF9YacLbixLvQ"

bot = Bot(token=TOKEN)
dp = Dispatcher()

@dp.bot_started()
async def on_bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text="Привет! Я Formula 100 AI. Напиши /start"
    )

@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    await event.message.answer("Приветствую! Бот работает. Отправь любое сообщение.")

@dp.message_created(Command('help'))
async def cmd_help(event: MessageCreated):
    await event.message.answer("Команды: /start, /help")

@dp.message_created()
async def echo(event: MessageCreated):
    text = event.message.body.text
    if text and text not in ('/start', '/help'):
        await event.message.answer(f"Вы написали: {text}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

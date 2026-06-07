import asyncio
import os
from aiomax import Bot
from aiomax.filters import F

# Получаем токен из переменной окружения (безопасно)
TOKEN = os.getenv("MAX_TOKEN")

if not TOKEN:
    raise RuntimeError("MAX_TOKEN not set")

bot = Bot(token=TOKEN)

# Обработчик команды /start
@bot.on_message(F.command("start"))
async def cmd_start(update):
    await bot.send_message(
        chat_id=update.message.recipient.chat_id,
        text="🧬 *Formula 100 AI*\n\nПривет! Я бот для подбора БАД.\n"
             "Используй /help для команд.",
        parse_mode="markdown"
    )

# Обработчик команды /help
@bot.on_message(F.command("help"))
async def cmd_help(update):
    await bot.send_message(
        chat_id=update.message.recipient.chat_id,
        text="/start — приветствие\n/help — справка\n\nСкоро добавлю анкету и рекомендации!"
    )

# Обработчик всех остальных сообщений (echo)
@bot.on_message()
async def echo(update):
    if update.message and update.message.body.text:
        await bot.send_message(
            chat_id=update.message.recipient.chat_id,
            text=f"Вы написали: {update.message.body.text}"
        )

async def main():
    await bot.start()
    await bot.start_polling()  # используем polling, он проще для тестов
    await bot.close()

if __name__ == "__main__":
    asyncio.run(main())

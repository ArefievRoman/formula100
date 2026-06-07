import asyncio
import os
from maxgram import Bot

# Бот сам возьмёт токен из переменной окружения MAX_TOKEN
bot = Bot(os.getenv("MAX_TOKEN"))

# Этот обработчик сработает, когда бот запустится
@bot.on("bot_started")
async def on_start(context):
    await context.reply("Привет! Я - твой персональный помощник 'Формула'.")

# Обработчик команды /start
@bot.command("start")
async def start_handler(context):
    await context.reply("Привет! Я бот 'Проект Эволюция' и я работаю!")

# Обработчик текстовых сообщений (бот просто повторит ваше сообщение)
@bot.on("message_created")
async def echo_handler(context):
    if context.message and "body" in context.message and "text" in context.message["body"]:
        user_text = context.message["body"]["text"]
        await context.reply(f"Вы сказали: {user_text}")

if __name__ == "__main__":
    try:
        bot.run()
    except KeyboardInterrupt:
        bot.stop()
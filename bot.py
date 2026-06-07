# bot.py
import asyncio
import logging
from maxapi import Bot, Dispatcher
from maxapi.types import BotStarted, Command, MessageCreated

# Укажите ваш токен напрямую или получите из переменных окружения
TOKEN = "ВАШ_ТОКЕН_БОТА"

# Настройка логирования (помогает отслеживать работу)
logging.basicConfig(level=logging.INFO)

bot = Bot(TOKEN)
dp = Dispatcher()

# Обработчик события "бот запущен" (когда кто-то нажал "Начать")
@dp.bot_started()
async def bot_started(event: BotStarted):
    await event.bot.send_message(
        chat_id=event.chat_id,
        text='Привет! Это Formula 100. Напиши /start, чтобы начать.'
    )

# Обработчик команды /start
@dp.message_created(Command('start'))
async def cmd_start(event: MessageCreated):
    await event.message.answer("Приветствую! Бот готов к работе.")

# Обработчик команды /help
@dp.message_created(Command('help'))
async def cmd_help(event: MessageCreated):
    await event.message.answer("Я бот для...")

# Обработчик для любого текстового сообщения (эхо)
@dp.message_created()
async def echo(event: MessageCreated):
    user_text = event.message.body.text
    if user_text and user_text not in ('/start', '/help'):
        await event.message.answer(f"Вы написали: {user_text}")

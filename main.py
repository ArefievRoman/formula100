from flask import Flask, request, jsonify
import requests
import os
import json

app = Flask(__name__)

# Получаем токен из переменных окружения (безопасно)
BOT_TOKEN = os.environ.get('MAX_TOKEN')
if not BOT_TOKEN:
    raise RuntimeError("MAX_TOKEN not set")

# Базовый URL для вызова методов API MAX
API_URL = "https://platform-api.max.ru"
HEADERS = {"Authorization": BOT_TOKEN}

@app.route('/webhook', methods=['POST'])
def webhook():
    """Обрабатывает входящие обновления от MAX"""
    update = request.json
    print(f"Получено обновление: {json.dumps(update, ensure_ascii=False)}")

    # Отвечаем MAX, что всё приняли (обязательно!)
    return jsonify({"status": "ok"}), 200

if __name__ == '__main__':
    # Запускаем сервер на порту, который ожидает Bothost
    port = int(os.environ.get('PORT', 3000))
    app.run(host='0.0.0.0', port=port)

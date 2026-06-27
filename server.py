import os
import json
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Токен твоего бота
API_TOKEN = "8768531793:AAH619M9uFehDFnUndSxyiSkisHiQJLk4lE"
bot = telebot.TeleBot(API_TOKEN)

app = FastAPI()

# База данных для хранения очереди команд: { user_id: { "command": "vibrate", "status": "pending" } }
device_commands = {}

def get_remote_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔋 Батарея", callback_data="cmd_battery"), InlineKeyboardButton("📳 Вибро", callback_data="cmd_vibrate"))
    markup.add(InlineKeyboardButton("📸 Сделать фото", callback_data="cmd_camera"))
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    bot.send_message(message.chat.id, "👋 Привет! Это твой универсальный пульт управления.", reply_markup=get_remote_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    bot.answer_callback_query(call.id)
    user_id = str(call.from_user.id)
    
    # Записываем команду для конкретного пользователя
    if call.data == "cmd_vibrate":
        device_commands[user_id] = "vibrate"
        bot.send_message(call.message.chat.id, "⏳ Отправлен сигнал вибрации на твой телефон...")
    elif call.data == "cmd_battery":
        device_commands[user_id] = "battery"
        bot.send_message(call.message.chat.id, "⏳ Запрашиваю статус батареи...")
    elif call.data == "cmd_camera":
        device_commands[user_id] = "camera"
        bot.send_message(call.message.chat.id, "⏳ Отправлен запрос на снимок...")

# --- API ДЛЯ ТЕЛЕФОНОВ (КЛИЕНТОВ) ---

@app.get("/get_command/{user_id}")
async def get_command(user_id: str):
    # Телефон друга обращается сюда, чтобы узнать, есть ли для него команда
    command = device_commands.get(user_id, None)
    if command:
        # Стираем команду из очереди, чтобы она не выполнилась дважды
        device_commands[user_id] = None
        return {"command": command}
    return {"command": "none"}

@app.post("/send_result/{user_id}")
async def send_result(user_id: str, request: Request):
    # Сюда телефон присылает текстовый ответ (например, заряд батареи)
    data = await request.json()
    result_text = data.get("text", "")
    bot.send_message(int(user_id), f"📱 **Ответ от твоего устройства:**\n\n{result_text}", parse_mode="Markdown")
    return {"status": "ok"}

@app.post("/send_photo/{user_id}")
async def send_photo(user_id: str, request: Request):
    # Сюда телефон загружает фото, а сервер пересылает его в ТГ
    form = await request.form()
    photo_file = form["photo"]
    photo_bytes = await photo_file.read()
    
    bot.send_photo(int(user_id), photo_bytes, caption="📸 Снимок с твоего устройства!")
    return {"status": "ok"}

# Точка запуска для Render
if __name__ == "__main__":
    import uvicorn
    # Запуск бота в отдельном потоке, чтобы он не мешал веб-серверу FastAPI
    import threading
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

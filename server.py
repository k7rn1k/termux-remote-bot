import os
import json
from fastapi import FastAPI, Request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, Update
import base64

# ТОКЕН ТВОЕГО БОТА (Проверь, чтобы он был точным!)
API_TOKEN = "8768531793:AAH619M9uFehDFnUndSxyiSkisHiQJLk4lE"
bot = telebot.TeleBot(API_TOKEN)

app = FastAPI()

# Ссылка на твой сервер Render (укажи её БЕЗ слэша на конце)
WEBHOOK_URL = "https://termux-remote-bot.onrender.com"

# --- СПИСОК РАЗРЕШЕННЫХ ДРУЗЕЙ И ИХ ID ---
# Обязательно впиши сюда свой реальный Telegram ID вместо "123456789"!
ALLOWED_DEVICES = {
    "1300270740": "Арсений (Мой телефон)",
}

device_commands = {}
current_target = {}

def get_devices_keyboard():
    markup = InlineKeyboardMarkup()
    for user_id, name in ALLOWED_DEVICES.items():
        markup.add(InlineKeyboardButton(f"📱 {name}", callback_data=f"target_{user_id}"))
    return markup

def get_remote_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔋 Батарея", callback_data="cmd_battery"), InlineKeyboardButton("📳 Вибро", callback_data="cmd_vibrate"))
    markup.add(InlineKeyboardButton("📸 Сделать фото", callback_data="cmd_camera"))
    markup.add(InlineKeyboardButton("⬅️ Назад", callback_data="cmd_back"))
    return markup

# Обработчик вебхука от Telegram
@app.post("/webhook")
async def telegram_webhook(request: Request):
    json_string = await request.json()
    update = Update.de_json(json_string)
    bot.process_new_updates([update])
    return {"status": "ok"}

# Настройка вебхука при запуске сервера
@app.on_event("startup")
def startup_event():
    bot.remove_webhook()
    bot.set_webhook(url=f"{WEBHOOK_URL}/webhook")
    print(f"🚀 Вебхук успешно установлен на {WEBHOOK_URL}/webhook")

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = str(message.from_user.id)
    if user_id not in ALLOWED_DEVICES:
        bot.send_message(message.chat.id, f"❌ Доступ закрыт. Твой ID: {user_id}. Добавь его в ALLOWED_DEVICES.")
        return
    bot.send_message(message.chat.id, "🤖 Центр Управления!\nВыбери устройство:", reply_markup=get_devices_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    user_id = str(call.from_user.id)
    
    if user_id not in ALLOWED_DEVICES:
        return

    if call.data.startswith("target_"):
        target_id = call.data.split("_")[1]
        current_target[chat_id] = target_id
        bot.edit_message_text(f"⚡️ Подключено к: **{ALLOWED_DEVICES[target_id]}**", chat_id, call.message.message_id, reply_markup=get_remote_keyboard(), parse_mode="Markdown")
        return

    if call.data == "cmd_back":
        bot.edit_message_text("🤖 Выбери устройство:", chat_id, call.message.message_id, reply_markup=get_devices_keyboard())
        return

    target_id = current_target.get(chat_id)
    if not target_id:
        return

    if call.data == "cmd_vibrate":
        device_commands[target_id] = "vibrate"
        bot.send_message(chat_id, f"⏳ Отправлено 'Вибро' на {ALLOWED_DEVICES[target_id]}...")
    elif call.data == "cmd_battery":
        device_commands[target_id] = "battery"
        bot.send_message(chat_id, f"⏳ Запрос батареи для {ALLOWED_DEVICES[target_id]}...")
    elif call.data == "cmd_camera":
        device_commands[target_id] = "camera"
        bot.send_message(chat_id, f"⏳ Запрос фото для {ALLOWED_DEVICES[target_id]}...")

# --- API ДЛЯ ТЕЛЕФОНОВ ---
@app.get("/get_command/{user_id}")
async def get_command(user_id: str):
    command = device_commands.get(user_id, None)
    if command:
        device_commands[user_id] = None
        return {"command": command}
    return {"command": "none"}

@app.post("/send_result/{user_id}")
async def send_result(user_id: str, request: Request):
    data = await request.json()
    bot.send_message(int(user_id), f"📱 **Ответ:**\n\n{data.get('text', '')}", parse_mode="Markdown")
    return {"status": "ok"}


@app.post("/send_photo/{user_id}")
async def send_photo(user_id: str, request: Request):
    data = await request.json()
    photo_base64 = data.get("photo", "")
    
    if photo_base64:
        # Декодируем строку обратно в байты изображения
        photo_bytes = base64.b64decode(photo_base64)
        device_name = ALLOWED_DEVICES.get(user_id, "Устройство")
        
        bot.send_photo(int(user_id), photo_bytes, caption=f"📸 Снимок с устройства {device_name}!")
        return {"status": "ok"}
    
    return {"status": "error", "message": "No photo data"}

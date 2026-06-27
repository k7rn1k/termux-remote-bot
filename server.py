import os
import json
import threading
from fastapi import FastAPI, Request
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton

# Токен твоего бота
API_TOKEN = "8768531793:AAH619M9uFehDFnUndSxyiSkisHiQJLk4lE"
bot = telebot.TeleBot(API_TOKEN)

app = FastAPI()

# --- СПИСОК РАЗРЕШЕННЫХ ДРУЗЕЙ И ИХ ID ---
# Впиши сюда свои ID и ID своих друзей, чтобы бот знал их по именам!
ALLOWED_DEVICES = {
    "1300270740": "основной телефон",
    "5412842997": "Ника",
}

# Хранилище команд { user_id: command }
device_commands = {}
# Хранилище текущего выбора в чате { chat_id: target_user_id }
current_target = {}

# Главное меню: выбор устройства
def get_devices_keyboard():
    markup = InlineKeyboardMarkup()
    for user_id, name in ALLOWED_DEVICES.items():
        markup.add(InlineKeyboardButton(f"📱 {name}", callback_data=f"target_{user_id}"))
    return markup

# Пульт управления конкретным устройством
def get_remote_keyboard():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("🔋 Батарея", callback_data="cmd_battery"), InlineKeyboardButton("📳 Вибро", callback_data="cmd_vibrate"))
    markup.add(InlineKeyboardButton("📸 Сделать фото", callback_data="cmd_camera"))
    markup.add(InlineKeyboardButton("⬅️ Назад к списку", callback_data="cmd_back"))
    return markup

@bot.message_handler(commands=['start'])
def start_message(message):
    user_id = str(message.from_user.id)
    if user_id not in ALLOWED_DEVICES:
        bot.send_message(message.chat.id, f"❌ Доступ закрыт. Твой ID: {user_id}. Попроси админа добавить тебя.")
        return
    
    bot.send_message(message.chat.id, "🤖 Добро пожаловать в Центр Управления!\nВыбери устройство, к которому хочешь подключиться:", reply_markup=get_devices_keyboard())

@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    bot.answer_callback_query(call.id)
    chat_id = call.message.chat.id
    user_id = str(call.from_user.id)
    
    # Проверка прав
    if user_id not in ALLOWED_DEVICES:
        return

    # Выбор устройства для управления
    if call.data.startswith("target_"):
        target_id = call.data.split("_")[1]
        current_target[chat_id] = target_id
        device_name = ALLOWED_DEVICES.get(target_id, "Неизвестное устройство")
        
        bot.edit_message_text(f"⚡️ Подключено к: **{device_name}**\nВыбери команду:", chat_id, call.message.message_id, reply_markup=get_remote_keyboard(), parse_mode="Markdown")
        return

    # Возврат к списку устройств
    if call.data == "cmd_back":
        bot.edit_message_text("🤖 Выбери устройство, к которому хочешь подключиться:", chat_id, call.message.message_id, reply_markup=get_devices_keyboard())
        return

    # Отправка команд на выбранное устройство
    target_id = current_target.get(chat_id)
    if not target_id:
        bot.send_message(chat_id, "⚠️ Сначала выбери устройство из списка!")
        return

    if call.data == "cmd_vibrate":
        device_commands[target_id] = "vibrate"
        bot.send_message(chat_id, f"⏳ Сигнал вибрации отправлен на телефон {ALLOWED_DEVICES[target_id]}...")
    elif call.data == "cmd_battery":
        device_commands[target_id] = "battery"
        bot.send_message(chat_id, f"⏳ Статус батареи запрошен у {ALLOWED_DEVICES[target_id]}...")
    elif call.data == "cmd_camera":
        device_commands[target_id] = "camera"
        bot.send_message(chat_id, f"⏳ Запрос на фото отправлен на {ALLOWED_DEVICES[target_id]}...")

# --- API ДЛЯ ТЕЛЕФОНОВ (КЛИЕНТОВ) ---

@app.get("/get_command/{user_id}")
async def get_command(user_id: str):
    command = device_commands.get(user_id, None)
    if command:
        device_commands[user_id] = None  # Очищаем очередь
        return {"command": command}
    return {"command": "none"}

@app.post("/send_result/{user_id}")
async def send_result(user_id: str, request: Request):
    data = await request.json()
    result_text = data.get("text", "")
    device_name = ALLOWED_DEVICES.get(user_id, "Устройство")
    # Отправляем ответ тому администратору, который сейчас управляет
    bot.send_message(int(user_id), f"📱 **Ответ от {device_name}:**\n\n{result_text}", parse_mode="Markdown")
    return {"status": "ok"}

@app.post("/send_photo/{user_id}")
async def send_photo(user_id: str, request: Request):
    form = await request.form()
    photo_file = form["photo"]
    photo_bytes = await photo_file.read()
    device_name = ALLOWED_DEVICES.get(user_id, "Устройство")
    
    bot.send_photo(int(user_id), photo_bytes, caption=f"📸 Снимок с устройства {device_name}!")
    return {"status": "ok"}

if __name__ == "__main__":
    import uvicorn
    threading.Thread(target=bot.infinity_polling, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)

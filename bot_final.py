#!/usr/bin/env python3
"""
Telegram бот для театральной мастерской "ИГРА" с webhook для Render
Версия 2.0 - защита от сна + webhook
"""

import os
import sqlite3
import logging
import threading
import time
import requests
from datetime import datetime
from flask import Flask, request
from apscheduler.schedulers.background import BackgroundScheduler
import telebot
from telebot import types

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8547352136:AAE1_t3mZcI8kmLXenqAu4WyTgSNRAvQcQs")
ADMIN_ID = os.getenv("ADMIN_ID", "482094409")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "")  # https://your-project.onrender.com
SELF_PING_URL = os.getenv("RENDER_EXTERNAL_URL", "")

bot = telebot.TeleBot(BOT_TOKEN)
DB_NAME = "filials_bookings.db"

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== FLASK СЕРВЕР ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "🎭 Театральная мастерская 'ИГРА' - бот работает! 👑"

@app.route('/health')
def health():
    return "OK", 200

@app.route('/ping')
def ping():
    return "pong 🏓", 200

@app.route('/status')
def status():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM bookings")
    bookings_count = cursor.fetchone()[0]
    cursor.execute("SELECT COUNT(*) FROM clients")
    clients_count = cursor.fetchone()[0]
    conn.close()
    
    return {
        "status": "online",
        "bookings": bookings_count,
        "clients": clients_count,
        "timestamp": datetime.now().isoformat()
    }

@app.route('/webhook', methods=['POST'])
def webhook():
    """Эндпоинт для webhook от Telegram"""
    if request.headers.get('content-type') == 'application/json':
        json_string = request.get_data().decode('utf-8')
        update = telebot.types.Update.de_json(json_string)
        bot.process_new_updates([update])
        return '', 200
    return 'Bad request', 400

def set_webhook():
    """Установка webhook"""
    if WEBHOOK_URL:
        try:
            bot.remove_webhook()
            time.sleep(1)
            full_url = f"{WEBHOOK_URL}/webhook"
            bot.set_webhook(url=full_url)
            logger.info(f"✅ Webhook установлен: {full_url}")
            print(f"✅ Webhook установлен: {full_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Ошибка установки webhook: {e}")
            return False
    else:
        logger.warning("⚠️ WEBHOOK_URL не установлен, используется polling")
        return False

def keep_alive():
    """Пинг самого себя для поддержания активности"""
    if SELF_PING_URL:
        try:
            response = requests.get(f"{SELF_PING_URL}/ping", timeout=10)
            logger.info(f"✅ Self-ping: {response.status_code}")
            print(f"✅ Ping sent at {datetime.now().strftime('%H:%M:%S')}")
        except Exception as e:
            logger.warning(f"⚠️ Ping failed: {e}")
            print(f"⚠️ Ping failed: {e}")

# ================== БАЗА ДАННЫХ ==================
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        phone TEXT,
        is_active INTEGER DEFAULT 1
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS clients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER UNIQUE,
        full_name TEXT NOT NULL,
        phone TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    ''')
    
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS bookings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        client_id INTEGER,
        filial_id INTEGER,
        service_type TEXT,
        notes TEXT,
        status TEXT DEFAULT 'new',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (client_id) REFERENCES clients (id),
        FOREIGN KEY (filial_id) REFERENCES filials (id)
    )
    ''')
    
    # Добавляем филиалы
    cursor.execute("SELECT COUNT(*) FROM filials")
    if cursor.fetchone()[0] == 0:
        test_filials = [
            ("Район Дзержинского", "ул. Дзержинского, д. 249/1", "+7 (967) 655-50-45"),
            ("ЮМР", "ул. Бульварное кольцо, д. 7/1", "+7 (967) 655-50-45"),
            ("ФМР", "ул. Ишунина, д. 6", "+7 (967) 655-50-45"),
            ("Немецкая деревня", "ул. Гете, д. 3", "+7 (967) 655-50-45"),
        ]
        
        for name, address, phone in test_filials:
            cursor.execute(
                "INSERT INTO filials (name, address, phone) VALUES (?, ?, ?)",
                (name, address, phone)
            )
    
    conn.commit()
    conn.close()
    logger.info("✅ База данных инициализирована")

# Словарь для состояний
user_states = {}

# ================== КЛАВИАТУРЫ ==================
def get_main_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("🎭 Записаться на занятие")
    btn2 = types.KeyboardButton("📍 Наши филиалы")
    btn3 = types.KeyboardButton("📞 Контакты")
    btn4 = types.KeyboardButton("ℹ️ О нас")
    btn5 = types.KeyboardButton("📋 Мои записи")
    btn6 = types.KeyboardButton("💬 Написать администратору")
    markup.add(btn1, btn2, btn3, btn4, btn5, btn6)
    return markup

def get_filials_keyboard():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM filials WHERE is_active = 1")
    filials = cursor.fetchall()
    conn.close()
    
    markup = types.InlineKeyboardMarkup()
    for filial_id, name in filials:
        markup.add(types.InlineKeyboardButton(name, callback_data=f"filial_{filial_id}"))
    markup.add(types.InlineKeyboardButton("❌ Отмена", callback_data="cancel"))
    return markup

# ================== КОМАНДЫ ==================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    init_db()
    
    welcome_text = f"""
👋 Привет, {first_name}!

🎭 Добро пожаловать в Театральную Мастерскую *"ИГРА"*!

✨ Что я умею:
• Записать вас на занятие в удобный филиал
• Показать контакты всех филиалов
• Сохранить ваши данные для связи
• Уведомить администратора о записи
• Принять ваше сообщение администратору

👇 Выберите действие ниже:
    """
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "💬 Написать администратору")
def start_direct_message(message):
    user_states[message.from_user.id] = {'mode': 'direct_message'}
    bot.send_message(
        message.chat.id,
        "💬 *Режим личного сообщения администратору*\n\nНапишите ваше сообщение, и я сразу перешлю его администратору.\n\nЧтобы отменить, отправьте /cancel",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('mode') == 'direct_message')
def process_direct_message(message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    username = f"@{message.from_user.username}" if message.from_user.username else "нет username"
    
    # Формируем сообщение для администратора
    admin_msg = f"""
📩 *НОВОЕ ЛИЧНОЕ СООБЩЕНИЕ*

👤 *От:* {user_name} ({username})
🆔 ID: `{user_id}`
⏰ *Время:* {datetime.now().strftime('%H:%M %d.%m.%Y')}

💬 *Сообщение:*
{message.text}

---
✏️ *Ответить:* tg://user?id={user_id}
    """
    
    try:
        # Отправляем администратору
        bot.send_message(ADMIN_ID, admin_msg, parse_mode="Markdown")
        
        # Подтверждение пользователю
        bot.reply_to(
            message,
            "✅ *Ваше сообщение отправлено администратору!*\n\nОн свяжется с вами в ближайшее время.",
            parse_mode="Markdown"
        )
        
        # Логируем
        logger.info(f"Личное сообщение от {user_id} отправлено администратору")
        
    except Exception as e:
        bot.reply_to(message, "❌ Ошибка отправки сообщения. Попробуйте позже.")
        logger.error(f"Ошибка отправки личного сообщения: {e}")
    
    # Очищаем состояние
    if user_id in user_states:
        del user_states[user_id]

@bot.message_handler(commands=['cancel'])
def cancel_action(message):
    user_id = message.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    bot.send_message(
        message.chat.id,
        "❌ Действие отменено.",
        reply_markup=get_main_keyboard()
    )

# ================== ЗАПИСЬ НА ЗАНЯТИЕ ==================
@bot.message_handler(func=lambda message: message.text == "🎭 Записаться на занятие")
def start_booking(message):
    bot.send_message(
        message.chat.id,
        "📍 *Выберите филиал:*",
        reply_markup=get_filials_keyboard(),
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('filial_'))
def process_filial(call):
    filial_id = int(call.data.split("_")[1])
    
    user_states[call.from_user.id] = {'filial_id': filial_id, 'step': 'waiting_name'}
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, address FROM filials WHERE id = ?", (filial_id,))
    filial = cursor.fetchone()
    conn.close()
    
    if filial:
        filial_name, address = filial
        bot.edit_message_text(
            f"📍 *Выбран филиал:* {filial_name}\n🏠 *Адрес:* {address}\n\n👤 *Введите ваше ФИО:*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'waiting_name')
def process_name(message):
    full_name = message.text.strip()
    
    if len(full_name) < 3:
        bot.send_message(message.chat.id, "❌ Введите полное ФИО (минимум 3 символа):")
        return
    
    user_states[message.from_user.id]['full_name'] = full_name
    user_states[message.from_user.id]['step'] = 'waiting_phone'
    
    bot.send_message(
        message.chat.id,
        f"👤 *ФИО:* {full_name}\n\n📞 *Теперь введите ваш номер телефона:*",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'waiting_phone')
def process_phone(message):
    phone = message.text.strip()
    
    # Простая валидация телефона
    digits = ''.join(filter(str.isdigit, phone))
    if len(digits) < 10:
        bot.send_message(message.chat.id, "❌ Неверный формат телефона. Введите еще раз:")
        return
    
    user_data = user_states[message.from_user.id]
    full_name = user_data['full_name']
    filial_id = user_data['filial_id']
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, address FROM filials WHERE id = ?", (filial_id,))
    filial = cursor.fetchone()
    conn.close()
    
    filial_name = filial[0] if filial else "Неизвестный филиал"
    filial_address = filial[1] if filial else ""
    
    # Подтверждение
    confirmation_text = f"""
✅ *ПОДТВЕРЖДЕНИЕ ЗАПИСИ*

📍 *Филиал:* {filial_name}
🏠 *Адрес:* {filial_address}
👤 *ФИО:* {full_name}
📞 *Телефон:* {phone}
🎭 *Услуга:* Запись на занятие

---
❓ *Всё верно?*
    """
    
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Да, всё верно", callback_data="confirm_yes"),
        types.InlineKeyboardButton("✏️ Исправить", callback_data="confirm_edit")
    )
    markup.row(types.InlineKeyboardButton("❌ Отменить", callback_data="confirm_no"))
    
    user_data['phone'] = phone
    user_data['filial_name'] = filial_name
    user_data['filial_address'] = filial_address
    user_data['step'] = 'waiting_confirmation'
    
    bot.send_message(
        message.chat.id,
        confirmation_text,
        reply_markup=markup,
        parse_mode="Markdown"
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def process_confirmation(call):
    action = call.data.split("_")[1]
    user_id = call.from_user.id
    
    if action == "no":
        bot.edit_message_text(
            "❌ *Запись отменена*",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        if user_id in user_states:
            del user_states[user_id]
        return
    
    if action == "edit":
        bot.edit_message_text(
            "📍 *Выберите филиал:*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_filials_keyboard(),
            parse_mode="Markdown"
        )
        if user_id in user_states:
            user_states[user_id]['step'] = 'waiting_name'
        return
    
    # Подтверждение записи
    user_data = user_states.get(user_id, {})
    
    if not user_data:
        bot.answer_callback_query(call.id, "⚠️ Данные устарели", show_alert=True)
        return
    
    # Сохраняем в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
        INSERT OR REPLACE INTO clients (user_id, full_name, phone, created_at)
        VALUES (?, ?, ?, ?)
        ''', (user_id, user_data['full_name'], user_data['phone'], datetime.now()))
        
        client_id = cursor.lastrowid
        
        cursor.execute('''
        INSERT INTO bookings (client_id, filial_id, service_type, notes, status)
        VALUES (?, ?, ?, ?, ?)
        ''', (
            client_id,
            user_data['filial_id'],
            "Запись на занятие",
            "Нет комментариев",
            'new'
        ))
        
        booking_id = cursor.lastrowid
        conn.commit()
        
        # Удаляем состояние
        if user_id in user_states:
            del user_states[user_id]
        
        # Сообщение клиенту
        success_text = f"""
🎉 *ЗАПИСЬ УСПЕШНО СОЗДАНА!*

✅ Ваша запись *#{booking_id}* в Театральную Мастерскую *"ИГРА"* принята!

📋 *Детали записи:*
📍 Филиал: {user_data['filial_name']}
🏠 Адрес: {user_data['filial_address']}
👤 ФИО: {user_data['full_name']}
📞 Телефон: {user_data['phone']}
🎭 Услуга: Запись на занятие

📞 *Мы свяжемся с вами в ближайшее время!*
Контакт для связи: +7 (967) 655-50-45
        """
        
        bot.edit_message_text(
            success_text,
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
        
        # Уведомление администратору
        admin_message = f"""
🎭 *НОВАЯ ЗАПИСЬ В ТЕАТРАЛЬНУЮ МАСТЕРСКУЮ "ИГРА"!*

📋 *Детали записи:*
🆔 ID: #{booking_id}
📍 Филиал: {user_data['filial_name']}
🏠 Адрес: {user_data['filial_address']}

👤 *Данные клиента:*
ФИО: {user_data['full_name']}
📞 Телефон: {user_data['phone']}
🆔 Telegram ID: `{user_id}`

🎭 *Услуга:* Запись на занятие

⏰ *Время записи:* {datetime.now().strftime('%H:%M %d.%m.%Y')}

📞 *Контактный телефон:* +7 (967) 655-50-45
        """
        
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            text="📋 Подробнее", 
            callback_data=f"admin_details_{booking_id}"
        ))
        markup.add(types.InlineKeyboardButton(
            text="💬 Написать клиенту", 
            url=f"tg://user?id={user_id}"
        ))
        
        bot.send_message(
            ADMIN_ID,
            admin_message,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Запись #{booking_id} создана, уведомление отправлено администратору")
        
    except Exception as e:
        logger.error(f"❌ Ошибка сохранения записи: {e}")
        bot.answer_callback_query(call.id, "❌ Ошибка сохранения", show_alert=True)
    finally:
        conn.close()

# ================== ЗАПУСК ==================
def run_flask():
    """Запуск Flask сервера"""
    port = int(os.environ.get('PORT', 10000))
    print(f"🌐 Запускаю Flask сервер на порту {port}...")
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

def run_bot():
    """Запуск бота с webhook или polling"""
    print("🤖 Инициализация бота...")
    
    if WEBHOOK_URL:
        print("🌐 Использую webhook...")
        if set_webhook():
            print("✅ Webhook настроен, сервер готов принимать запросы")
        else:
            print("🔄 Не удалось настроить webhook, использую polling...")
            bot.remove_webhook()
            bot.polling(none_stop=True, interval=0, timeout=20)
    else:
        print("🔄 Использую polling...")
        bot.remove_webhook()
        bot.polling(none_stop=True, interval=0, timeout=20)

if __name__ == "__main__":
    print("=" * 50)
    print("🎭 БОТ ТЕАТРАЛЬНОЙ МАСТЕРСКОЙ 'ИГРА' v2.0")
    print("=" * 50)
    print(f"✅ Токен: {'Установлен' if BOT_TOKEN else '❌ Нет!'}")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"🌐 Webhook URL: {WEBHOOK_URL or '❌ Не установлен'}")
    print(f"🏓 Ping URL: {SELF_PING_URL or '❌ Не установлен'}")
    print("=" * 50)
    
    # Инициализация БД
    init_db()
    
    # Запуск планировщика пингов
    scheduler = BackgroundScheduler()
    scheduler.add_job(keep_alive, 'interval', minutes=4)
    scheduler.start()
    print("⏰ Планировщик пингов запущен (каждые 4 минуты)")
    
    # Первый пинг
    keep_alive()
    
    # Запуск Flask в отдельном потоке
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    # Ждём запуска сервера
    time.sleep(2)
    
    # Запуск бота
    run_bot()

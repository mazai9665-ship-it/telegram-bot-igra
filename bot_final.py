#!/usr/bin/env python3
"""
Telegram бот для театральной мастерской "ИГРА" 
Полная рабочая версия для Render
"""

import os
import sqlite3
import logging
from datetime import datetime
import telebot
from telebot import types
from flask import Flask
import threading

# ================== НАСТРОЙКИ ==================
BOT_TOKEN = os.getenv("BOT_TOKEN", "8547352136:AAE1_t3mZcI8kmLXenqAu4WyTgSNRAvQcQs")
ADMIN_ID = os.getenv("ADMIN_ID", "482094409")
bot = telebot.TeleBot(BOT_TOKEN)
DB_NAME = "filials_bookings.db"

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== FLASK СЕРВЕР ДЛЯ RENDER ==================
app = Flask(__name__)

@app.route('/')
def home():
    return "Бот театральной мастерской 'ИГРА' работает!"

@app.route('/health')
def health():
    return "OK", 200

def run_flask():
    """Запуск веб-сервера для Render"""
    port = int(os.environ.get('PORT', 10000))
    app.run(host='0.0.0.0', port=port, debug=False, use_reloader=False)

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
        user_id INTEGER,
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
    
    # Добавляем филиалы с emoji
    cursor.execute("SELECT COUNT(*) FROM filials")
    if cursor.fetchone()[0] == 0:
        test_filials = [
            ("🏢 Район Дзержинского", "ул. Дзержинского, д. 249/1", "+7 (967) 655-50-45"),
            ("🏬 ЮМР", "ул. Бульварное кольцо, д. 7/1", "+7 (967) 655-50-45"),
            ("🏪 ФМР", "ул. Ишунина, д. 6", "+7 (967) 655-50-45"),
            ("🏘️ Немецкая деревня", "ул. Гете, д. 3", "+7 (967) 655-50-45"),
        ]
        
        for name, address, phone in test_filials:
            cursor.execute(
                "INSERT INTO filials (name, address, phone) VALUES (?, ?, ?)",
                (name, address, phone)
            )
    
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

# Словарь для хранения состояний пользователей
user_states = {}

# ================== КЛАВИАТУРЫ ==================
def get_main_keyboard():
    """Главное меню с emoji"""
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    btn1 = types.KeyboardButton("📝 Записаться на занятие")
    btn2 = types.KeyboardButton("🏢 Наши филиалы")
    btn3 = types.KeyboardButton("📞 Контакты")
    btn4 = types.KeyboardButton("ℹ️ О нас")
    btn5 = types.KeyboardButton("👤 Мои записи")
    markup.add(btn1, btn2, btn3, btn4, btn5)
    return markup

def get_filials_keyboard():
    """Клавиатура выбора филиала"""
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

# ================== КОМАНДЫ И КНОПКИ ==================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Команда /start"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    init_db()
    
    welcome_text = f"""🎭 Привет, {first_name}!

Добро пожаловать в Театральную Мастерскую "ИГРА"!

✨ Что я умею:
• Записать вас на занятие в удобный филиал
• Показать контакты всех филиалов  
• Сохранить ваши данные для связи
• Уведомить администратора о записи

Выберите действие ниже 👇"""
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "📝 Записаться на занятие")
def start_booking(message):
    """Начало записи"""
    bot.send_message(
        message.chat.id,
        "🏢 Выберите филиал:",
        reply_markup=get_filials_keyboard()
    )

@bot.message_handler(func=lambda message: message.text == "🏢 Наши филиалы")
def show_filials(message):
    """Показать филиалы"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, address, phone FROM filials WHERE is_active = 1")
    filials = cursor.fetchall()
    conn.close()
    
    response = "🏢 НАШИ ФИЛИАЛЫ:\n\n"
    
    for name, address, phone in filials:
        response += f"{name}\n"
        response += f"📍 Адрес: {address}\n"
        response += f"📞 Телефон: {phone}\n"
        response += "──────────────\n"
    
    bot.send_message(message.chat.id, response)

@bot.message_handler(func=lambda message: message.text == "📞 Контакты")
def show_contacts(message):
    """Показать контакты"""
    contacts_text = """📞 КОНТАКТЫ ТЕАТРАЛЬНОЙ МАСТЕРСКОЙ "ИГРА"

📱 Телефон: +7 (967) 655-50-45
🕐 Время работы: 16:00-21:00

🌐 Ссылки:
• Сайт: https://taplink.cc/te_ma_igra
• Telegram: https://t.me/te_ma_igra_krasnodar
• Instagram: https://www.instagram.com/te_ma_igra

📍 Наши филиалы:
🏢 Район Дзержинского
🏬 ЮМР  
🏪 ФМР
🏘️ Немецкая деревня"""
    
    bot.send_message(message.chat.id, contacts_text)

@bot.message_handler(func=lambda message: message.text == "ℹ️ О нас")
def show_about(message):
    """Информация о нас"""
    about_text = """🎭 ТЕАТРАЛЬНАЯ МАСТЕРСКАЯ "ИГРА"

Мы — театральная мастерская, где каждый может раскрыть свой творческий потенциал!

✨ Почему выбирают нас:
✅ Профессиональные педагоги с театральным образованием
✅ 4 удобных филиала в Краснодаре
✅ Занятия для детей и взрослых
✅ Индивидуальный подход к каждому ученику
✅ Постановка спектаклей и участие в фестивалях

🎯 Наши направления:
• Актерское мастерство
• Сценическая речь
• Театральные постановки
• Ораторское искусство
• Развитие уверенности в себе

Присоединяйтесь к нам и откройте в себе актёрский талант! ✨"""
    
    bot.send_message(message.chat.id, about_text)

@bot.message_handler(func=lambda message: message.text == "👤 Мои записи")
def show_my_bookings(message):
    """Показать записи пользователя - ИСПРАВЛЕННАЯ ВЕРСИЯ"""
    user_id = message.from_user.id
    
    # Отладка
    print(f"🔍 Кнопка 'Мои записи' нажата пользователем {user_id}")
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Ищем клиента в базе
    cursor.execute("SELECT id, full_name, phone FROM clients WHERE user_id = ?", (user_id,))
    client = cursor.fetchone()
    
    if not client:
        print(f"📭 Пользователь {user_id} не найден в базе клиентов")
        bot.send_message(message.chat.id, "📭 У вас еще нет записей. Запишитесь на первое занятие!")
        conn.close()
        return
    
    client_id, client_name, client_phone = client
    print(f"👤 Найден клиент: {client_name}, ID в базе: {client_id}")
    
    # Ищем записи клиента
    cursor.execute('''
    SELECT b.id, f.name, b.service_type, b.created_at, b.status
    FROM bookings b
    JOIN filials f ON b.filial_id = f.id
    WHERE b.client_id = ?
    ORDER BY b.created_at DESC
    LIMIT 10
    ''', (client_id,))
    
    bookings = cursor.fetchall()
    conn.close()
    
    if not bookings:
        print(f"📭 У клиента {client_id} нет записей")
        bot.send_message(message.chat.id, "📭 У вас нет активных записей.")
        return
    
    print(f"📋 Найдено {len(bookings)} записей для клиента {client_id}")
    
    response = "📋 ВАШИ ЗАПИСИ:\n\n"
    
    for booking_id, filial_name, service, created_at, status in bookings:
        status_icon = "✅" if status == "confirmed" else "🔄" if status == "new" else "❌"
        response += f"{status_icon} Запись #{booking_id}\n"
        response += f"🏢 Филиал: {filial_name}\n"
        response += f"🎭 Услуга: {service}\n"
        response += f"📅 Дата: {created_at[:10]}\n"
        response += f"📊 Статус: {status}\n"
        response += "──────────────\n"
    
    bot.send_message(message.chat.id, response)

# ================== ПРОЦЕСС ЗАПИСИ ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith('filial_'))
def process_filial(call):
    """Обработка выбора филиала"""
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
            f"✅ Выбран филиал: {filial_name}\n"
            f"📍 Адрес: {address}\n\n"
            f"👤 Теперь введите ваше ФИО полностью:\n"
            f"(Например: Иванов Иван Иванович)",
            call.message.chat.id,
            call.message.message_id
        )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'waiting_name')
def process_name(message):
    """Обработка ввода имени"""
    full_name = message.text.strip()
    
    if len(full_name) < 5:
        bot.send_message(message.chat.id, "❌ Введите полное ФИО (минимум 5 символов):")
        return
    
    user_states[message.from_user.id]['full_name'] = full_name
    user_states[message.from_user.id]['step'] = 'waiting_phone'
    
    bot.send_message(
        message.chat.id,
        f"👤 ФИО: {full_name}\n\n"
        f"📞 Теперь введите ваш номер телефона:\n"
        f"(Например: +79161234567 или 89161234567)"
    )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'waiting_phone')
def process_phone(message):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    
    if not any(char.isdigit() for char in phone) or len(phone) < 10:
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
    
    confirmation_text = f"""✅ ПОДТВЕРЖДЕНИЕ ЗАПИСИ

Филиал: {filial_name}
Адрес: {filial_address}
ФИО: {full_name}
Телефон: {phone}
Услуга: 🎭 Запись на занятие

Всё верно?"""
    
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
        reply_markup=markup
    )

@bot.callback_query_handler(func=lambda call: call.data.startswith('confirm_'))
def process_confirmation(call):
    """Обработка подтверждения"""
    action = call.data.split("_")[1]
    user_id = call.from_user.id
    
    if action == "no":
        bot.edit_message_text(
            "❌ Запись отменена",
            call.message.chat.id,
            call.message.message_id
        )
        if user_id in user_states:
            del user_states[user_id]
        return
    
    if action == "edit":
        bot.edit_message_text(
            "🏢 Выберите филиал:",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_filials_keyboard()
        )
        if user_id in user_states:
            user_states[user_id]['step'] = 'waiting_name'
        return
    
    user_data = user_states.get(user_id, {})
    
    if not user_data:
        bot.answer_callback_query(call.id, "❌ Данные устарели", show_alert=True)
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
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
        "🎭 Запись на занятие",
        "Нет комментариев",
        'new'
    ))
    
    booking_id = cursor.lastrowid
    conn.commit()
    conn.close()
    
    if user_id in user_states:
        del user_states[user_id]
    
    success_text = f"""🎉 ЗАПИСЬ УСПЕШНО СОЗДАНА!

Ваша запись #{booking_id} в Театральную Мастерскую "ИГРА" принята!

📋 Детали записи:
🏢 Филиал: {user_data['filial_name']}
📍 Адрес: {user_data['filial_address']}
👤 ФИО: {user_data['full_name']}
📞 Телефон: {user_data['phone']}
🎭 Услуга: Запись на занятие

Мы свяжемся с вами в ближайшее время!

📞 Контакт для связи: +7 (967) 655-50-45"""
    
    bot.edit_message_text(
        success_text,
        call.message.chat.id,
        call.message.message_id
    )
    
    try:
        admin_message = f"""🎭 НОВАЯ ЗАПИСЬ В ТЕАТРАЛЬНУЮ МАСТЕРСКУЮ "ИГРА"!

📋 Детали записи:
ID: #{booking_id}
Филиал: {user_data['filial_name']}
Адрес: {user_data['filial_address']}

👤 Данные клиента:
ФИО: {user_data['full_name']}
Телефон: {user_data['phone']}
Telegram ID: {user_id}

🎭 Услуга: Запись на занятие

⏰ Время записи: {datetime.now().strftime('%H:%M %d.%m.%Y')}

📞 Контактный телефон: +7 (967) 655-50-45"""
        
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
            reply_markup=markup
        )
        
        print(f"✅ Уведомление отправлено администратору {ADMIN_ID}")
        
    except Exception as e:
        print(f"❌ Ошибка отправки уведомления: {e}")

@bot.callback_query_handler(func=lambda call: call.data == 'cancel')
def cancel_booking(call):
    """Отмена записи"""
    user_id = call.from_user.id
    if user_id in user_states:
        del user_states[user_id]
    
    bot.edit_message_text(
        "❌ Запись отменена",
        call.message.chat.id,
        call.message.message_id
    )

# ================== ЗАПУСК ==================
def run_bot():
    """Запуск Telegram бота"""
    print("🤖 Запускаю Telegram бота...")
    bot.polling(none_stop=True, interval=0, timeout=30)

if __name__ == "__main__":
    init_db()
    
    print("=" * 50)
    print("БОТ ТЕАТРАЛЬНОЙ МАСТЕРСКОЙ 'ИГРА'")
    print("=" * 50)
    print(f"Токен: {'Установлен' if BOT_TOKEN else 'Нет!'}")
    print(f"Админ ID: {ADMIN_ID}")
    print("=" * 50)
    print("🌐 Запускаю веб-сервер и бота...")
    print("=" * 50)
    
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    
    run_bot()

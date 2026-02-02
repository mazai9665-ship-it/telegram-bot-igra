#!/usr/bin/env python3
"""
Telegram бот для театральной мастерской "ИГРА" - Рабочая версия для Render
Используем pyTelegramBotAPI вместо aiogram
"""

import os
import sqlite3
import logging
from datetime import datetime
import telebot
from telebot import types

# ================== НАСТРОЙКИ ==================
# ТОКЕН БОТА из переменных окружения Render
BOT_TOKEN = os.getenv("BOT_TOKEN", "8547352136:AAE1_t3mZcI8kmLXenqAu4WyTgSNRAvQcQs")

# ID администратора из переменных окружения Render
ADMIN_ID = os.getenv("ADMIN_ID", "482094409")

# Настройки базы данных
DB_NAME = "filials_bookings.db"

# Инициализация бота
bot = telebot.TeleBot(BOT_TOKEN)

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== БАЗА ДАННЫХ ==================
def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Таблица филиалов
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS filials (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        address TEXT,
        phone TEXT,
        is_active INTEGER DEFAULT 1
    )
    ''')
    
    # Таблица клиентов
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
    
    # Таблица записей
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
    
    # Добавляем филиалы театральной мастерской
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

# ================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ==================
def get_main_keyboard():
    """Главная клавиатура"""
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

# Словарь для хранения состояний пользователей
user_states = {}

# ================== ОБРАБОТЧИКИ КОМАНД ==================
@bot.message_handler(commands=['start'])
def cmd_start(message):
    """Обработка команды /start"""
    user_id = message.from_user.id
    first_name = message.from_user.first_name
    
    # Инициализируем БД
    init_db()
    
    welcome_text = f"""
🎭 Привет, {first_name}!

Добро пожаловать в Театральную Мастерскую *"ИГРА"*!

✨ *Что я умею:*
• Записать вас на занятие в удобный филиал
• Показать контакты всех филиалов
• Сохранить ваши данные для связи
• Уведомить администратора о записи

Выберите действие ниже 👇
    """
    
    bot.send_message(
        message.chat.id,
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "📝 Записаться на занятие")
def start_booking(message):
    """Начало процесса записи"""
    bot.send_message(
        message.chat.id,
        "🏢 *Выберите филиал:*\n\nУкажите, в какой филиал вы хотите записаться:",
        reply_markup=get_filials_keyboard(),
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: message.text == "🏢 Наши филиалы")
def show_filials(message):
    """Показать все филиалы"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, address, phone FROM filials WHERE is_active = 1")
    filials = cursor.fetchall()
    conn.close()
    
    response = "🏢 *НАШИ ФИЛИАЛЫ:*\n\n"
    
    for name, address, phone in filials:
        response += f"*{name}*\n"
        response += f"📍 {address}\n"
        response += f"📞 {phone}\n"
        response += "──────────────\n"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "📞 Контакты")
def show_contacts(message):
    """Показать контакты"""
    contacts_text = """
📞 *КОНТАКТЫ ТЕАТРАЛЬНОЙ МАСТЕРСКОЙ "ИГРА":*

📱 *Основной телефон:*
+7 (967) 655-50-45

🕐 *Время работы:*
Ежедневно с 16:00 до 21:00

🌐 *Сайт и социальные сети:*
[Сайт](https://taplink.cc/te_ma_igra)
[Telegram канал](https://t.me/te_ma_igra_krasnodar)
[Instagram](https://www.instagram.com/te_ma_igra?igsh=MW0zNGNidmh0OXdtZw==)

📍 *Наши филиалы в Краснодаре:*
• 🏢 Район Дзержинского
• 🏬 ЮМР
• 🏪 ФМР  
• 🏘️ Немецкая деревня
    """
    
    bot.send_message(message.chat.id, contacts_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "ℹ️ О нас")
def show_about(message):
    """Показать информацию"""
    about_text = """
🎭 *ТЕАТРАЛЬНАЯ МАСТЕРСКАЯ "ИГРА"*

Мы — театральная мастерская, где каждый может раскрыть свой творческий потенциал!

✨ *Почему выбирают нас:*
✅ Профессиональные педагоги с театральным образованием
✅ 4 удобных филиала в Краснодаре
✅ Занятия для детей и взрослых
✅ Индивидуальный подход к каждому ученику
✅ Постановка спектаклей и участие в фестивалях

🎯 *Наши направления:*
• Актерское мастерство
• Сценическая речь
• Театральные постановки
• Ораторское искусство
• Развитие уверенности в себе

Присоединяйтесь к нам и откройте в себе актёрский талант! ✨
    """
    
    bot.send_message(message.chat.id, about_text, parse_mode="Markdown")

@bot.message_handler(func=lambda message: message.text == "👤 Мои записи")
def show_my_bookings(message):
    """Показать записи пользователя"""
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Находим клиента
    cursor.execute("SELECT id FROM clients WHERE user_id = ?", (user_id,))
    client = cursor.fetchone()
    
    if not client:
        bot.send_message(message.chat.id, "📭 У вас еще нет записей.")
        conn.close()
        return
    
    client_id = client[0]
    
    # Находим записи клиента
    cursor.execute('''
    SELECT b.id, f.name, b.service_type, b.created_at, b.status
    FROM bookings b
    JOIN filials f ON b.filial_id = f.id
    WHERE b.client_id = ?
    ORDER BY b.created_at DESC
    ''', (client_id,))
    
    bookings = cursor.fetchall()
    conn.close()
    
    if not bookings:
        bot.send_message(message.chat.id, "📭 У вас нет активных записей.")
        return
    
    response = "📋 *ВАШИ ЗАПИСИ:*\n\n"
    
    for booking_id, filial_name, service, created_at, status in bookings:
        status_icon = "✅" if status == "confirmed" else "🔄" if status == "new" else "❌"
        response += f"{status_icon} *Запись #{booking_id}*\n"
        response += f"🏢 Филиал: {filial_name}\n"
        response += f"🎭 Услуга: {service}\n"
        response += f"📅 Дата: {created_at[:10]}\n"
        response += f"📊 Статус: {status}\n"
        response += "──────────────\n"
    
    bot.send_message(message.chat.id, response, parse_mode="Markdown")

# ================== ОБРАБОТКА ВЫБОРА ФИЛИАЛА ==================
@bot.callback_query_handler(func=lambda call: call.data.startswith('filial_'))
def process_filial(call):
    """Обработка выбора филиала"""
    filial_id = int(call.data.split("_")[1])
    
    # Сохраняем выбранный филиал
    user_states[call.from_user.id] = {'filial_id': filial_id, 'step': 'waiting_name'}
    
    # Получаем информацию о филиале
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, address FROM filials WHERE id = ?", (filial_id,))
    filial = cursor.fetchone()
    conn.close()
    
    if filial:
        filial_name, address = filial
        bot.edit_message_text(
            f"✅ *Выбран филиал:* {filial_name}\n"
            f"📍 Адрес: {address}\n\n"
            f"👤 *Теперь введите ваше ФИО полностью:*\n"
            f"(Например: Иванов Иван Иванович)",
            call.message.chat.id,
            call.message.message_id,
            parse_mode="Markdown"
        )
    else:
        bot.answer_callback_query(call.id, "❌ Филиал не найден", show_alert=True)

# ================== ОБРАБОТКА ВВОДА ДАННЫХ ==================
@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'waiting_name')
def process_name(message):
    """Обработка ввода имени"""
    full_name = message.text.strip()
    
    if len(full_name) < 5:
        bot.send_message(message.chat.id, "❌ Введите полное ФИО (минимум 5 символов):")
        return
    
    # Сохраняем имя
    user_states[message.from_user.id]['full_name'] = full_name
    user_states[message.from_user.id]['step'] = 'waiting_phone'
    
    bot.send_message(
        message.chat.id,
        f"👤 *ФИО:* {full_name}\n\n"
        f"📞 *Теперь введите ваш номер телефона:*\n"
        f"(Например: +79161234567 или 89161234567)",
        parse_mode="Markdown"
    )

@bot.message_handler(func=lambda message: user_states.get(message.from_user.id, {}).get('step') == 'waiting_phone')
def process_phone(message):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    
    # Простая валидация
    if not any(char.isdigit() for char in phone) or len(phone) < 10:
        bot.send_message(message.chat.id, "❌ Неверный формат телефона. Введите еще раз:")
        return
    
    user_data = user_states[message.from_user.id]
    full_name = user_data['full_name']
    filial_id = user_data['filial_id']
    
    # Получаем информацию о филиале
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, address FROM filials WHERE id = ?", (filial_id,))
    filial = cursor.fetchone()
    conn.close()
    
    filial_name = filial[0] if filial else "Неизвестный филиал"
    filial_address = filial[1] if filial else ""
    
    # Показываем подтверждение
    confirmation_text = f"""
✅ *ПОДТВЕРЖДЕНИЕ ЗАПИСИ*

*Филиал:* {filial_name}
*Адрес:* {filial_address}
*ФИО:* {full_name}
*Телефон:* {phone}
*Услуга:* 🎭 Запись на занятие

Всё верно?
    """
    
    # Клавиатура подтверждения
    markup = types.InlineKeyboardMarkup()
    markup.row(
        types.InlineKeyboardButton("✅ Да, всё верно", callback_data="confirm_yes"),
        types.InlineKeyboardButton("✏️ Исправить", callback_data="confirm_edit")
    )
    markup.row(types.InlineKeyboardButton("❌ Отменить", callback_data="confirm_no"))
    
    # Сохраняем данные для подтверждения
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

# ================== ОБРАБОТКА ПОДТВЕРЖДЕНИЯ ==================
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
            "🏢 *Выберите филиал:*",
            call.message.chat.id,
            call.message.message_id,
            reply_markup=get_filials_keyboard(),
            parse_mode="Markdown"
        )
        if user_id in user_states:
            user_states[user_id]['step'] = 'waiting_name'
        return
    
    # Подтверждение записи (action == "yes")
    user_data = user_states.get(user_id, {})
    
    if not user_data:
        bot.answer_callback_query(call.id, "❌ Данные устарели", show_alert=True)
        return
    
    # Сохраняем в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Сохраняем/обновляем клиента
    cursor.execute('''
    INSERT OR REPLACE INTO clients (user_id, full_name, phone, created_at)
    VALUES (?, ?, ?, ?)
    ''', (user_id, user_data['full_name'], user_data['phone'], datetime.now()))
    
    client_id = cursor.lastrowid
    
    # Сохраняем запись
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
    
    # Удаляем состояние пользователя
    if user_id in user_states:
        del user_states[user_id]
    
    # Сообщение клиенту
    success_text = f"""
🎉 *ЗАПИСЬ УСПЕШНО СОЗДАНА!*

Ваша запись *#{booking_id}* в Театральную Мастерскую "ИГРА" принята!

📋 *Детали записи:*
🏢 Филиал: {user_data['filial_name']}
📍 Адрес: {user_data['filial_address']}
👤 ФИО: {user_data['full_name']}
📞 Телефон: {user_data['phone']}
🎭 Услуга: Запись на занятие

Мы свяжемся с вами в ближайшее время для подтверждения!

📞 *Контакт для связи:*
+7 (967) 655-50-45
    """
    
    bot.edit_message_text(
        success_text,
        call.message.chat.id,
        call.message.message_id,
        parse_mode="Markdown"
    )
    
    # Уведомление администратору
    try:
        admin_message = f"""
🎭 *НОВАЯ ЗАПИСЬ В ТЕАТРАЛЬНУЮ МАСТЕРСКУЮ "ИГРА"!* 🎭

📋 *Детали записи:*
ID: #{booking_id}
Филиал: {user_data['filial_name']}
Адрес: {user_data['filial_address']}

👤 *Данные клиента:*
ФИО: *{user_data['full_name']}*
Телефон: `{user_data['phone']}`
Telegram ID: `{user_id}`

🎭 *Услуга:*
Запись на занятие

⏰ *Время записи:*
{datetime.now().strftime('%H:%M %d.%m.%Y')}

📞 *Контактный телефон:*
+7 (967) 655-50-45
            # Уведомление администратору
    try:
        admin_message = f"""
🎭 *НОВАЯ ЗАПИСЬ В ТЕАТРАЛЬНУЮ МАСТЕРСКУЮ "ИГРА"!* 🎭

📋 *Детали записи:*
ID: #{booking_id}
Филиал: {user_data['filial_name']}
Адрес: {user_data['filial_address']}

👤 *Данные клиента:*
ФИО: *{user_data['full_name']}*
Телефон: `{user_data['phone']}` 📞
Telegram ID: `{user_id}`

🎭 *Услуга:*
Запись на занятие

⏰ *Время записи:*
{datetime.now().strftime('%H:%M %d.%m.%Y')}

➖➖➖➖➖➖➖➖➖➖
📞 *Телефон студии:* +7 (967) 655-50-45
        """
        
        # Только рабочие кнопки
        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("📋 Подробнее", callback_data=f"admin_details_{booking_id}"),
            types.InlineKeyboardButton("💬 Написать", url=f"tg://user?id={user_id}")
        )
        
        bot.send_message(
            ADMIN_ID,
            admin_message,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Уведомление отправлено администратору {ADMIN_ID}")
        print(f"✅ УВЕДОМЛЕНИЕ ОТПРАВЛЕНО НА ID: {ADMIN_ID}")
        
    except Exception as e:
        logger.error(f"❌ Ошибка отправки уведомления: {e}")
        print(f"❌ ОШИБКА ОТПРАВКИ: {e}")
        
        # Пробуем отправить без кнопок
        try:
            simple_msg = f"🎭 Новая запись #{booking_id}\n👤 {user_data['full_name']}\n📞 {user_data['phone']}"
            bot.send_message(ADMIN_ID, simple_msg)
            print("✅ Простое уведомление отправлено")
        except:
            print("❌ Не удалось отправить даже простое сообщение")
        
        # Кнопки для администратора
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(
            text="📋 Подробнее и действия", 
            callback_data=f"admin_details_{booking_id}"
        ))
        markup.add(types.InlineKeyboardButton(
            text="💬 Написать клиенту", 
            url=f"tg://user?id={user_id}"
        ))
        markup.add(types.InlineKeyboardButton(
            text="📞 Позвонить клиенту", 
            url=f"tel:{user_data['phone']}"
        ))
        
        bot.send_message(
            ADMIN_ID,
            admin_message,
            reply_markup=markup,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Уведомление отправлено администратору {ADMIN_ID}")
        
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления: {e}")

# ================== ОТМЕНА ==================
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

# ================== ЗАПУСК БОТА ==================
if __name__ == "__main__":
    # Инициализация БД
    init_db()
    
    print("=" * 50)
    print("🎭 БОТ ТЕАТРАЛЬНОЙ МАСТЕРСКОЙ 'ИГРА'")
    print("=" * 50)
    print(f"✅ Токен: {'Установлен' if BOT_TOKEN else 'Нет!'}")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"💾 База данных: {DB_NAME}")
    print(f"📞 Контактный телефон: +7 (967) 655-50-45")
    print(f"🕐 Время работы: 16:00-21:00")
    print("=" * 50)
    print("🌐 Запущен в облаке Render.com!")
    print("🤖 Бот работает 24/7")
    print("=" * 50)
    
    # Запускаем бота
    bot.polling(none_stop=True, interval=0)

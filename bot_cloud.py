#!/usr/bin/env python3
"""
Telegram бот для записи в театральную мастерскую "ИГРА" - облачная версия
Автор: AI Assistant
"""

import asyncio
import sqlite3
import logging
import os
import sys
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import (
    Message, CallbackQuery, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    ReplyKeyboardMarkup, KeyboardButton
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

# ================== НАСТРОЙКИ ==================
# ТОКЕН БОТА из переменных окружения Render
BOT_TOKEN = os.getenv("BOT_TOKEN", "8547352136:AAE1_t3mZcI8kmLXenqAu4WyTgSNRAvQcQs")

# ID администратора из переменных окружения Render
ADMIN_ID = os.getenv("ADMIN_ID", "482094409")
ADMIN_IDS = [int(ADMIN_ID)]

# Настройки базы данных
DB_NAME = "filials_bookings.db"

# Логирование
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# ================== ИНИЦИАЛИЗАЦИЯ ==================
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

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

# ================== СОСТОЯНИЯ (FSM) ==================
class BookingStates(StatesGroup):
    """Состояния для записи"""
    choosing_filial = State()
    entering_name = State()
    entering_phone = State()
    confirmation = State()

# ================== КЛАВИАТУРЫ ==================
def get_main_keyboard():
    """Главная клавиатура"""
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📝 Записаться на занятие")],
            [KeyboardButton(text="🏢 Наши филиалы"), KeyboardButton(text="📞 Контакты")],
            [KeyboardButton(text="ℹ️ О нас"), KeyboardButton(text="👤 Мои записи")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_filials_keyboard():
    """Клавиатура выбора филиала"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT id, name FROM filials WHERE is_active = 1")
    filials = cursor.fetchall()
    conn.close()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    
    for filial_id, name in filials:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(text=name, callback_data=f"filial_{filial_id}")
        ])
    
    keyboard.inline_keyboard.append([
        InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
    ])
    
    return keyboard

def get_services_keyboard():
    """Клавиатура выбора услуги"""
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🎭 Запись на занятие", callback_data="service_booking")],
            [
                InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_filial"),
                InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")
            ]
        ]
    )
    
    return keyboard

# ================== КОМАНДЫ ==================
@dp.message(Command("start"))
async def cmd_start(message: Message):
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
    
    await message.answer(
        welcome_text,
        reply_markup=get_main_keyboard(),
        parse_mode="Markdown"
    )

@dp.message(F.text == "📝 Записаться на занятие")
async def start_booking(message: Message, state: FSMContext):
    """Начало процесса записи"""
    await message.answer(
        "🏢 *Выберите филиал:*\n\n"
        "Укажите, в какой филиал вы хотите записаться:",
        reply_markup=get_filials_keyboard(),
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.choosing_filial)

@dp.message(F.text == "🏢 Наши филиалы")
async def show_filials(message: Message):
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
    
    await message.answer(response, parse_mode="Markdown")

@dp.message(F.text == "📞 Контакты")
async def show_contacts(message: Message):
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
    
    await message.answer(contacts_text, parse_mode="Markdown")

@dp.message(F.text == "ℹ️ О нас")
async def show_about(message: Message):
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
    
    await message.answer(about_text, parse_mode="Markdown")

@dp.message(F.text == "👤 Мои записи")
async def show_my_bookings(message: Message):
    """Показать записи пользователя"""
    user_id = message.from_user.id
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Находим клиента
    cursor.execute("SELECT id FROM clients WHERE user_id = ?", (user_id,))
    client = cursor.fetchone()
    
    if not client:
        await message.answer("📭 У вас еще нет записей.")
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
        await message.answer("📭 У вас нет активных записей.")
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
    
    await message.answer(response, parse_mode="Markdown")

# ================== ВЫБОР ФИЛИАЛА ==================
@dp.callback_query(F.data.startswith("filial_"))
async def process_filial(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора филиала"""
    filial_id = int(callback.data.split("_")[1])
    
    # Сохраняем выбранный филиал
    await state.update_data(filial_id=filial_id)
    
    # Получаем информацию о филиале
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, address FROM filials WHERE id = ?", (filial_id,))
    filial = cursor.fetchone()
    conn.close()
    
    if filial:
        filial_name, address = filial
        await callback.message.edit_text(
            f"✅ *Выбран филиал:* {filial_name}\n"
            f"📍 Адрес: {address}\n\n"
            f"👤 *Теперь введите ваше ФИО полностью:*\n"
            f"(Например: Иванов Иван Иванович)",
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.entering_name)
    else:
        await callback.answer("❌ Филиал не найден", show_alert=True)

# ================== ВВОД ИМЕНИ ==================
@dp.message(BookingStates.entering_name)
async def process_name(message: Message, state: FSMContext):
    """Обработка ввода имени"""
    full_name = message.text.strip()
    
    if len(full_name) < 5:
        await message.answer("❌ Введите полное ФИО (минимум 5 символов):")
        return
    
    await state.update_data(full_name=full_name)
    
    await message.answer(
        f"👤 *ФИО:* {full_name}\n\n"
        f"📞 *Теперь введите ваш номер телефона:*\n"
        f"(Например: +79161234567 или 89161234567)",
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.entering_phone)

# ================== ВВОД ТЕЛЕФОНА ==================
@dp.message(BookingStates.entering_phone)
async def process_phone(message: Message, state: FSMContext):
    """Обработка ввода телефона"""
    phone = message.text.strip()
    
    # Простая валидация
    if not any(char.isdigit() for char in phone) or len(phone) < 10:
        await message.answer("❌ Неверный формат телефона. Введите еще раз:")
        return
    
    await state.update_data(phone=phone)
    
    await message.answer(
        f"📞 *Телефон:* {phone}\n\n"
        f"🎭 *Подтвердите запись на занятие:*",
        reply_markup=get_services_keyboard(),
        parse_mode="Markdown"
    )

# ================== ВЫБОР УСЛУГИ ==================
@dp.callback_query(F.data.startswith("service_"))
async def process_service(callback: CallbackQuery, state: FSMContext):
    """Обработка выбора услуги"""
    service_code = callback.data.split("_")[1]
    
    if service_code == "back_to_filial":
        await callback.message.edit_text(
            "🏢 *Выберите филиал:*",
            reply_markup=get_filials_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.choosing_filial)
        return
    
    if service_code == "cancel":
        await callback.message.edit_text("❌ Запись отменена")
        await state.clear()
        return
    
    # Сохраняем услугу и переходим к подтверждению
    await state.update_data(service_type="🎭 Запись на занятие", notes="Нет комментариев")
    
    # Получаем все данные
    data = await state.get_data()
    
    # Получаем информацию о филиале
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT name, address FROM filials WHERE id = ?", (data['filial_id'],))
    filial = cursor.fetchone()
    conn.close()
    
    filial_name = filial[0] if filial else "Неизвестный филиал"
    filial_address = filial[1] if filial else ""
    
    # Формируем подтверждение
    confirmation_text = f"""
✅ *ПОДТВЕРЖДЕНИЕ ЗАПИСИ*

*Филиал:* {filial_name}
*Адрес:* {filial_address}
*ФИО:* {data['full_name']}
*Телефон:* {data['phone']}
*Услуга:* 🎭 Запись на занятие

Всё верно?
    """
    
    # Клавиатура подтверждения
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, всё верно", callback_data="confirm_yes"),
                InlineKeyboardButton(text="✏️ Исправить", callback_data="confirm_edit")
            ],
            [
                InlineKeyboardButton(text="❌ Отменить", callback_data="confirm_no")
            ]
        ]
    )
    
    await callback.message.edit_text(
        confirmation_text,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await state.set_state(BookingStates.confirmation)

# ================== ПОДТВЕРЖДЕНИЕ И СОХРАНЕНИЕ ==================
@dp.callback_query(F.data.startswith("confirm_"))
async def process_confirmation(callback: CallbackQuery, state: FSMContext):
    """Обработка подтверждения"""
    action = callback.data.split("_")[1]
    
    if action == "no":
        await callback.message.edit_text("❌ Запись отменена")
        await state.clear()
        return
    
    if action == "edit":
        await callback.message.edit_text(
            "🏢 *Выберите филиал:*",
            reply_markup=get_filials_keyboard(),
            parse_mode="Markdown"
        )
        await state.set_state(BookingStates.choosing_filial)
        return
    
    # Подтверждение записи
    data = await state.get_data()
    user_id = callback.from_user.id
    
    # Сохраняем в БД
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Сохраняем/обновляем клиента
    cursor.execute('''
    INSERT OR REPLACE INTO clients (user_id, full_name, phone, created_at)
    VALUES (?, ?, ?, ?)
    ''', (user_id, data['full_name'], data['phone'], datetime.now()))
    
    client_id = cursor.lastrowid
    
    # Сохраняем запись
    cursor.execute('''
    INSERT INTO bookings (client_id, filial_id, service_type, notes, status)
    VALUES (?, ?, ?, ?, ?)
    ''', (
        client_id,
        data['filial_id'],
        data['service_type'],
        data['notes'],
        'new'
    ))
    
    booking_id = cursor.lastrowid
    
    # Получаем информацию о филиале для уведомления
    cursor.execute("SELECT name, address FROM filials WHERE id = ?", (data['filial_id'],))
    filial = cursor.fetchone()
    
    conn.commit()
    conn.close()
    
    # Сохраняем в текстовый файл на всякий случай
    try:
        with open("записи_клиентов.txt", "a", encoding="utf-8") as f:
            f.write("\n" + "="*50 + "\n")
            f.write(f"ЗАПИСЬ #{booking_id}\n")
            f.write(f"Дата: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n")
            f.write(f"ФИО: {data['full_name']}\n")
            f.write(f"Телефон: {data['phone']}\n")
            f.write(f"Филиал: {filial[0]}\n")
            f.write(f"Адрес: {filial[1]}\n")
            f.write(f"Услуга: {data['service_type']}\n")
            f.write("="*50 + "\n")
        logger.info(f"✅ Запись #{booking_id} сохранена в файл")
    except Exception as e:
        logger.error(f"⚠️ Не удалось сохранить в файл: {e}")
    
    # Сообщение клиенту
    success_text = f"""
🎉 *ЗАПИСЬ УСПЕШНО СОЗДАНА!*

Ваша запись *#{booking_id}* в Театральную Мастерскую "ИГРА" принята!

📋 *Детали записи:*
🏢 Филиал: {filial[0]}
📍 Адрес: {filial[1]}
👤 ФИО: {data['full_name']}
📞 Телефон: {data['phone']}
🎭 Услуга: Запись на занятие

Мы свяжемся с вами в ближайшее время для подтверждения!

📞 *Контакт для связи:*
+7 (967) 655-50-45
    """
    
    await callback.message.edit_text(
        success_text,
        parse_mode="Markdown"
    )
    
    # ================== УВЕДОМЛЕНИЕ АДМИНИСТРАТОРУ ==================
    for admin_id in ADMIN_IDS:
        try:
            admin_message = f"""
🎭 *НОВАЯ ЗАПИСЬ В ТЕАТРАЛЬНУЮ МАСТЕРСКУЮ "ИГРА"!* 🎭

📋 *Детали записи:*
ID: #{booking_id}
Филиал: {filial[0]}
Адрес: {filial[1]}

👤 *Данные клиента:*
ФИО: *{data['full_name']}*
Телефон: `{data['phone']}`
Telegram ID: `{user_id}`

🎭 *Услуга:*
Запись на занятие

⏰ *Время записи:*
{datetime.now().strftime('%H:%M %d.%m.%Y')}

📞 *Контактный телефон:*
+7 (967) 655-50-45
            """
            
            # Кнопки для администратора
            contact_keyboard = InlineKeyboardMarkup(
                inline_keyboard=[
                    [
                        InlineKeyboardButton(
                            text="📋 Подробнее и действия",
                            callback_data=f"admin_details_{booking_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="💬 Написать клиенту",
                            url=f"tg://user?id={user_id}"
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text="📞 Позвонить клиенту",
                            url=f"tel:{data['phone']}"
                        )
                    ]
                ]
            )
            
            await bot.send_message(
                admin_id,
                admin_message,
                reply_markup=contact_keyboard,
                parse_mode="Markdown"
            )
            
            logger.info(f"✅ Уведомление отправлено администратору {admin_id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")
            
            # Пробуем отправить БЕЗ клавиатуры
            try:
                simple_message = f"""
🎭 Новая запись #{booking_id}
👤 *{data['full_name']}*
📞 `{data['phone']}`
🏢 {filial[0]}
⏰ {datetime.now().strftime('%H:%M')}
                """
                await bot.send_message(admin_id, simple_message, parse_mode="Markdown")
                logger.info(f"✅ Простое уведомление отправлено")
            except Exception as e2:
                logger.error(f"❌ Не удалось отправить: {e2}")
    
    await state.clear()

# ================== ОБРАБОТКА КНОПОК АДМИНА ==================
@dp.callback_query(F.data.startswith("admin_details_"))
async def admin_details(callback: CallbackQuery):
    """Показать детали записи администратору"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    booking_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Получаем полную информацию о записи
    cursor.execute('''
    SELECT 
        b.id, c.full_name, c.phone, c.email, 
        f.name, f.address, f.phone as filial_phone,
        b.service_type, b.notes, b.status, b.created_at
    FROM bookings b
    JOIN clients c ON b.client_id = c.id
    JOIN filials f ON b.filial_id = f.id
    WHERE b.id = ?
    ''', (booking_id,))
    
    record = cursor.fetchone()
    conn.close()
    
    if not record:
        await callback.answer("❌ Запись не найдена", show_alert=True)
        return
    
    (rec_id, full_name, phone, email, filial_name, 
     filial_address, filial_phone, service_type, 
     notes, status, created_at) = record
    
    # Формируем детальное сообщение
    details_text = f"""
📋 *ПОЛНЫЕ ДАННЫЕ ЗАПИСИ #{rec_id}*

*👤 КЛИЕНТ:*
ФИО: *{full_name}*
Телефон: `{phone}`
Email: {email if email else "не указан"}
Статус: {status}

*🏢 ФИЛИАЛ:*
Название: {filial_name}
Адрес: {filial_address}
Телефон: {filial_phone}

*🎭 УСЛУГА:*
{service_type}

*📝 КОММЕНТАРИЙ:*
{notes}

*⏰ ДАТА И ВРЕМЯ:*
Запись: {created_at}
    """
    
    # Кнопки действий для админа
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="✅ Подтвердить",
                    callback_data=f"admin_confirm_{rec_id}"
                ),
                InlineKeyboardButton(
                    text="❌ Отклонить", 
                    callback_data=f"admin_reject_{rec_id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="💬 Написать в Telegram",
                    url=f"tg://user?id={callback.from_user.id}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="📞 Позвонить клиенту",
                    url=f"tel:{phone}"
                )
            ],
            [
                InlineKeyboardButton(
                    text="⬅️ Назад к списку",
                    callback_data="admin_back"
                )
            ]
        ]
    )
    
    # Редактируем сообщение с деталями
    try:
        await callback.message.edit_text(
            details_text,
            reply_markup=keyboard,
            parse_mode="Markdown"
        )
        await callback.answer()
    except Exception as e:
        logger.error(f"Ошибка редактирования сообщения: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)

@dp.callback_query(F.data == "admin_back")
async def admin_back(callback: CallbackQuery):
    """Вернуться к списку записей"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT b.id, c.full_name, c.phone, f.name, b.created_at
    FROM bookings b
    JOIN clients c ON b.client_id = c.id
    JOIN filials f ON b.filial_id = f.id
    ORDER BY b.id DESC
    LIMIT 5
    ''')
    
    records = cursor.fetchall()
    conn.close()
    
    if not records:
        await callback.message.edit_text("📭 Записей пока нет")
        return
    
    response = "📋 *ПОСЛЕДНИЕ ЗАПИСИ:*\n\n"
    for rec_id, name, phone, filial, created in records:
        response += f"*#{rec_id}* • {created[11:16]}\n"
        response += f"👤 {name}\n"
        response += f"📞 {phone}\n"
        response += f"🏢 {filial}\n"
        response += "──────────────\n"
    
    # Кнопка для просмотра деталей каждой записи
    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    for rec_id, name, phone, filial, created in records:
        keyboard.inline_keyboard.append([
            InlineKeyboardButton(
                text=f"📋 #{rec_id} - {name[:10]}...",
                callback_data=f"admin_details_{rec_id}"
            )
        ])
    
    await callback.message.edit_text(
        response,
        reply_markup=keyboard,
        parse_mode="Markdown"
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("admin_confirm_"))
async def admin_confirm_booking(callback: CallbackQuery):
    """Подтвердить запись"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    booking_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Обновляем статус записи
    cursor.execute(
        "UPDATE bookings SET status = 'confirmed' WHERE id = ?",
        (booking_id,)
    )
    
    # Получаем данные клиента для уведомления
    cursor.execute('''
    SELECT c.user_id, c.full_name, b.service_type
    FROM bookings b
    JOIN clients c ON b.client_id = c.id
    WHERE b.id = ?
    ''', (booking_id,))
    
    client_data = cursor.fetchone()
    conn.commit()
    conn.close()
    
    if client_data:
        user_id, full_name, service = client_data
        # Уведомляем клиента
        try:
            await bot.send_message(
                user_id,
                f"✅ *Ваша запись #{booking_id} подтверждена!*\n\n"
                f"Услуга: {service}\n"
                f"Мы ждем вас в назначенное время!\n\n"
                f"📞 *Контакт для связи:*\n"
                f"+7 (967) 655-50-45\n\n"
                f"🌐 *Наши соцсети:*\n"
                f"[Telegram канал](https://t.me/te_ma_igra_krasnodar)\n"
                f"[Instagram](https://www.instagram.com/te_ma_igra?igsh=MW0zNGNidmh0OXdtZw==)"
            )
        except:
            pass  # Если клиент заблокировал бота
    
    await callback.answer(f"✅ Запись #{booking_id} подтверждена", show_alert=True)
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"✅ Запись #{booking_id} подтверждена!\n"
        f"Клиент уведомлен.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")
            ]]
        )
    )

@dp.callback_query(F.data.startswith("admin_reject_"))
async def admin_reject_booking(callback: CallbackQuery):
    """Отклонить запись"""
    if callback.from_user.id not in ADMIN_IDS:
        await callback.answer("⛔ Нет доступа", show_alert=True)
        return
    
    booking_id = int(callback.data.split("_")[2])
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Обновляем статус записи
    cursor.execute(
        "UPDATE bookings SET status = 'rejected' WHERE id = ?",
        (booking_id,)
    )
    
    # Получаем данные клиента для уведомления
    cursor.execute('''
    SELECT c.user_id, c.full_name
    FROM bookings b
    JOIN clients c ON b.client_id = c.id
    WHERE b.id = ?
    ''', (booking_id,))
    
    client_data = cursor.fetchone()
    conn.commit()
    conn.close()
    
    if client_data:
        user_id, full_name = client_data
        # Уведомляем клиента
        try:
            await bot.send_message(
                user_id,
                f"❌ *Ваша запись #{booking_id} отклонена*\n\n"
                f"По вопросам обращайтесь по телефону:\n"
                f"+7 (967) 655-50-45"
            )
        except:
            pass
    
    await callback.answer(f"❌ Запись #{booking_id} отклонена", show_alert=True)
    
    # Обновляем сообщение
    await callback.message.edit_text(
        f"❌ Запись #{booking_id} отклонена!\n"
        f"Клиент уведомлен.",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_back")
            ]]
        )
    )

# ================== АДМИН КОМАНДЫ ==================
@dp.message(Command("admin"))
async def admin_panel(message: Message):
    """Панель администратора"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Доступ запрещен")
        return
    
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📋 Все записи", callback_data="admin_all_bookings")],
            [InlineKeyboardButton(text="📤 Экспорт данных", callback_data="admin_export")]
        ]
    )
    
    await message.answer(
        "🔐 *ПАНЕЛЬ АДМИНИСТРАТОРА*\n\n"
        "Выберите действие:",
        reply_markup=keyboard,
        parse_mode="Markdown"
    )

@dp.callback_query(F.data == "admin_stats")
async def show_stats(callback: CallbackQuery):
    """Показать статистику"""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute("SELECT COUNT(*) FROM clients")
    total_clients = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bookings")
    total_bookings = cursor.fetchone()[0]
    
    cursor.execute("SELECT COUNT(*) FROM bookings WHERE DATE(created_at) = DATE('now')")
    today_bookings = cursor.fetchone()[0]
    
    cursor.execute('''
    SELECT f.name, COUNT(b.id) as count
    FROM bookings b
    JOIN filials f ON b.filial_id = f.id
    GROUP BY f.name
    ORDER BY count DESC
    ''')
    filials_stats = cursor.fetchall()
    
    conn.close()
    
    stats_text = f"""
📊 *СТАТИСТИКА ТЕАТРАЛЬНОЙ МАСТЕРСКОЙ "ИГРА"*

👥 Всего клиентов: *{total_clients}*
📅 Всего записей: *{total_bookings}*
🎭 Записей сегодня: *{today_bookings}*

🏢 *Популярность филиалов:*
    """
    
    for filial, count in filials_stats:
        stats_text += f"\n{filial}: *{count}* записей"
    
    await callback.message.edit_text(
        stats_text,
        parse_mode="Markdown"
    )

@dp.message(Command("last"))
async def show_last_records(message: Message):
    """Показать последние записи (для админа)"""
    if message.from_user.id not in ADMIN_IDS:
        await message.answer("⛔ Нет доступа")
        return
    
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('''
    SELECT b.id, c.full_name, c.phone, f.name, b.service_type, b.created_at
    FROM bookings b
    JOIN clients c ON b.client_id = c.id
    JOIN filials f ON b.filial_id = f.id
    ORDER BY b.id DESC
    LIMIT 10
    ''')
    
    records = cursor.fetchall()
    conn.close()
    
    if not records:
        await message.answer("📭 Записей пока нет")
        return
    
    response = "📋 *ПОСЛЕДНИЕ 10 ЗАПИСЕЙ:*\n\n"
    for rec_id, name, phone, filial, service, created in records:
        response += f"*#{rec_id}* • {created[11:16]}\n"
        response += f"👤 {name}\n"
        response += f"📞 {phone}\n"
        response += f"🏢 {filial}\n"
        response += f"🎭 {service}\n"
        response += "──────────────\n"
    
    await message.answer(response, parse_mode="Markdown")

# ================== ЗАПУСК БОТА ДЛЯ ОБЛАКА ==================
async def main():
    """Основная функция запуска бота для облака"""
    # Инициализация БД
    init_db()
    
    print("=" * 50)
    print("🎭 БОТ ТЕАТРАЛЬНОЙ МАСТЕРСКОЙ 'ИГРА'")
    print("=" * 50)
    print(f"✅ Токен: {'Установлен' if BOT_TOKEN else 'Нет!'}")
    print(f"👑 Админ ID: {ADMIN_IDS}")
    print(f"💾 База данных: {DB_NAME}")
    print(f"📞 Контактный телефон: +7 (967) 655-50-45")
    print(f"🕐 Время работы: 16:00-21:00")
    print("=" * 50)
    print("🌐 Запущен в облаке Render.com!")
    print("🤖 Бот работает 24/7")
    print("=" * 50)
    
    # Запуск бота в режиме long-polling (для облака)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
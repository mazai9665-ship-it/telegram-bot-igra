#!/usr/bin/env python3
"""
Telegram бот для театральной мастерской "ИГРА" - облачная версия
"""

import asyncio
import sqlite3
import logging
import os
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
# ТОКЕН БОТА из переменных окружения
BOT_TOKEN = os.getenv("BOT_TOKEN", "8547352136:AAE1_t3mZcI8kmLXenqAu4WyTgSNRAvQcQs")
# ID администратора из переменных окружения
ADMIN_ID = os.getenv("ADMIN_ID", "482094409")
ADMIN_IDS = [int(ADMIN_ID)]

# Настройки базы данных (используем SQLite в памяти для облака)
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

# ... ВСТАВЬТЕ СЮДА ВЕСЬ ВАШ ТЕКУЩИЙ КОД БОТА ...
# (весь код от def init_db() до async def main())

# ТОЛЬКО ИЗМЕНИТЕ ФУНКЦИЮ main():
async def main():
    """Основная функция запуска бота"""
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
    print("🌐 Запущен в облаке!")
    print("🤖 Бот работает 24/7")
    print("=" * 50)
    
    # Запускаем бота в режиме long-polling
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Бот остановлен")
    except Exception as e:
        print(f"\n❌ Критическая ошибка: {e}")
        import traceback
        traceback.print_exc()
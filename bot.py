# bot.py - ИСПРАВЛЕННАЯ ВЕРСИЯ
import asyncio
import html
import datetime
from datetime import date, datetime, timedelta

import logging
import pytz
import random
import sqlite3
import re
import json
from typing import Dict, Any
from collections import defaultdict
import time

from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    ReplyKeyboardMarkup, KeyboardButton, 
    InlineKeyboardMarkup, InlineKeyboardButton,
    FSInputFile
)
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

# Библиотеки для фильтрации
from better_profanity import profanity
profanity.load_censor_words()

# Наши модули
from texts import BotTexts
from gamification import GamificationSystem, get_leaderboard
from lunar import LunarScience
from rhythm_core import (
    get_cns_phase, get_female_phase, 
    get_combined_recommendation, get_hiit_recommendation,
    get_hiit_protocol, calculate_fat_burn_window
)
from simple_rag import SimpleRAG


# ==================== ЗАЩИТА И БЕЗОПАСНОСТЬ ====================
from collections import defaultdict
import time
import asyncio
import re

import os
from dotenv import load_dotenv

from mindful_eating import start_mindful_eating
from utils import get_user, update_user_db, has_access, check_rate_limit

from menu import menu_router
from mindful_eating import mindful_router

# В начале bot.py, после других импортов добавь:
from menu import menu_router
from mindful_eating import mindful_router
from water_calculator import water_router  # 👈 ДОБАВЛЯЕМ

from genetics_engine import GeneticsEngine

# Импорт модуля статистики
from statistics import show_statistics_menu, handle_stat_callback


# Загружаем переменные окружения из .env файла
load_dotenv()

# Получаем токен из переменной окружения
BOT_TOKEN = os.getenv('TELEGRAM_TOKEN')


RATE_LIMIT = {
    'per_second': 1,     # максимум сообщений в секунду
    'per_minute': 20,    # максимум сообщений в минуту
    'per_hour': 100      # максимум сообщений в час
}



def sanitize_input(text: str, max_length: int = 100) -> str:
    """Очищает ввод от опасных символов"""
    if not text:
        return ""
    
    text = text[:max_length]
    
    # Блокируем SQL-инъекции
    dangerous = [';', '--', '/*', '*/', 'xp_', 'exec', 'drop', 'truncate', 'alter', 'delete']
    for d in dangerous:
        text = text.replace(d, '')
    
    # Экранируем кавычки
    text = text.replace("'", "''")
    
    return text

def validate_numeric(value: str, min_val=None, max_val=None) -> bool:
    """Проверяет, что ввод — число в допустимом диапазоне"""
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except ValueError:
        return False

# Словарь для отслеживания попыток
registration_attempts = defaultdict(list)

def check_registration_spam(user_id):
    """Проверяет, не спамит ли пользователь регистрацией"""
    now = time.time()
    # Очищаем старые попытки (старше 1 часа)
    registration_attempts[user_id] = [t for t in registration_attempts[user_id] if now - t < 3600]
    
    # Если больше 3 попыток за час
    if len(registration_attempts[user_id]) >= 3:
        return False
    
    # Добавляем новую попытку
    registration_attempts[user_id].append(now)
    return True

# В bot.py, после импортов, где-то в начале файла добавляем:

# Глобальные переменные
gamification = None  # Будет инициализирован в main()
lunar = LunarScience()
rag = None

# ==================== СИСТЕМА НАЧИСЛЕНИЯ ОЧКОВ ====================
async def award_points(user_id: int, action: str, message: types.Message = None):
    """Начислить очки и уведомить пользователя"""
    global gamification
    
    # Проверяем, что gamification инициализирован
    if gamification is None:
        print(f"⚠️ Gamification not initialized, can't award points for {action}")
        return
    
    try:
        result = gamification.add_points(user_id, action)
        
        if 'error' in result:
            return
        
        if result['points_added'] != 0 and message:
            points_text = f"+{result['points_added']} ⭐"
            
            if result.get('new_title'):
                await message.answer(
                    f"🎉 **ПОВЫШЕНИЕ!**\n\n"
                    f"Ты достиг(ла) звания:\n"
                    f"{result['new_title']['emoji']} **{result['new_title']['name']}**\n"
                    f"{result['new_title']['desc']}"
                )
            
            if result.get('new_achievements'):
                for ach in result['new_achievements']:
                    await message.answer(
                        f"🏆 **НОВОЕ ДОСТИЖЕНИЕ!**\n"
                        f"{ach['emoji']} {ach['name']}\n"
                        f"{ach['desc']}\n"
                        f"+{ach['points']} ⭐"
                    )
            
            if not result.get('new_title') and not result.get('new_achievements'):
                await message.answer(f"✨ {points_text} очков биохакера!")
    
    except Exception as e:
        logger.error(f"Error awarding points: {e}")


# ==================== КОНФИГУРАЦИЯ ====================

ADMIN_ID = 8427751802
DB_NAME = 'users.db'

# ==================== ИНИЦИАЛИЗАЦИЯ ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=None))
dp = Dispatcher(storage=storage)
scheduler = AsyncIOScheduler()

# Глобальные переменные
gamification = None
lunar = LunarScience()
rag = None  

# ==================== БАЗА ДАННЫХ ====================
def init_db():
    """Инициализация базы данных со всеми полями"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            
            # Таблица пользователей
            cur.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY, 
                    real_name TEXT, 
                    power_name TEXT, 
                    gender_type INTEGER,
                    work_type TEXT,
                    hiit_time TEXT,
                    wake_time TEXT, 
                    tz TEXT, 
                    rhythm_start TEXT,
                    cycle_start TEXT,
                    cycle_length INTEGER DEFAULT 28,
                    last_pulse_delta INTEGER DEFAULT 0,
                    weight REAL DEFAULT 0,
                    waist REAL DEFAULT 0,
                    hips REAL DEFAULT 0,
                    chest REAL DEFAULT 0,
                    resting_hr INTEGER DEFAULT 0,
                    registered_date TEXT,
                    -- Геймификация
                    bio_points INTEGER DEFAULT 0,
                    achievements TEXT DEFAULT '[]',
                    streak_days INTEGER DEFAULT 0,
                    last_activity DATE,
                    -- Биоритмы
                    birth_date DATE,
                    birth_date_consent BOOLEAN DEFAULT 0,
                    last_phys_feeling INTEGER,
                    last_emot_feeling INTEGER,
                    last_intel_feeling INTEGER,
                    phys_phase_shift INTEGER DEFAULT 0,
                    emot_phase_shift INTEGER DEFAULT 0,
                    intel_phase_shift INTEGER DEFAULT 0,
                    calibration_count INTEGER DEFAULT 0,
                    last_calibration_ask DATE,
                    -- Чит-мил
                    cheat_day DATE,
                    -- Водный модуль
                    water_goal INTEGER DEFAULT 2000,
                    water_consumed_today INTEGER DEFAULT 0,
                    water_preferences TEXT DEFAULT '{}',
                    daily_protein INTEGER DEFAULT 70,
                    -- Генетика
                    genetics_mthfr TEXT,
                    genetics_fto TEXT,
                    genetics_actn3 TEXT,
                    genetics_trpm6 TEXT,
                    genetics_consent INTEGER DEFAULT 0,
                    -- Подписки
                    subscription_status TEXT DEFAULT 'free',
                    subscription_until DATE,
                    goal TEXT DEFAULT 'weight_loss'
                )
            ''')
            
            # Таблица для утренних замеров
            cur.execute('''
                CREATE TABLE IF NOT EXISTS morning_checkin (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    sleep_quality INTEGER,
                    pulse_lie INTEGER,
                    pulse_stand INTEGER,
                    pulse_delta INTEGER
                )
            ''')
            
            # Таблица для вечерних опросов
            cur.execute('''
                CREATE TABLE IF NOT EXISTS evening_audit (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    nutrition_timing INTEGER,
                    nutrition_mindful INTEGER,
                    hiit_done INTEGER,
                    motivation INTEGER,
                    energy INTEGER,
                    emotional INTEGER
                )
            ''')
            
            # Таблица для недельных замеров
            cur.execute('''
                CREATE TABLE IF NOT EXISTS weekly_metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    weight REAL,
                    waist REAL,
                    hips REAL,
                    chest REAL
                )
            ''')
            
            # Таблица для вызовов психолога
            cur.execute('''
                CREATE TABLE IF NOT EXISTS psychologist_calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    status TEXT DEFAULT 'pending'
                )
            ''')
            
            # Таблица для логов воды
            cur.execute('''
                CREATE TABLE IF NOT EXISTS water_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    date TEXT,
                    amount INTEGER,
                    timestamp TEXT
                )
            ''')
            
            conn.commit()
            logger.info("Database initialized successfully")
            return True
    except Exception as e:
        logger.error(f"Database initialization error: {e}")
        return False


# ==================== ПРОВЕРКА ДОСТУПА ====================

def get_all_users():
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            return conn.cursor().execute("SELECT * FROM users").fetchall()
    except Exception as e:
        logger.error(f"Error getting all users: {e}")
        return []


def add_user(user_id: int, data: Dict[str, Any]):
    """Добавляет нового пользователя в базу данных"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT OR REPLACE INTO users (user_id, {columns}) VALUES (?, {placeholders})"
            cur.execute(query, (user_id, *data.values()))
            conn.commit()
            print(f"✅ Пользователь {user_id} успешно добавлен в БД")
            return True
    except Exception as e:
        print(f"❌ Ошибка добавления пользователя {user_id}: {e}")
        return False

def save_morning_checkin(user_id: int, data: Dict[str, Any]):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO morning_checkin 
                (user_id, date, sleep_quality, pulse_lie, pulse_stand, pulse_delta) 
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                user_id, 
                date.today().isoformat(),
                data.get('sleep_quality'),
                data.get('pulse_lie'),
                data.get('pulse_stand'),
                data.get('pulse_delta')
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Error saving morning checkin: {e}")

def save_evening_audit(user_id: int, answers: Dict[str, int]):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO evening_audit 
                (user_id, date, nutrition_timing, nutrition_mindful, hiit_done, motivation, energy, emotional) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                user_id,
                date.today().isoformat(),
                answers.get('q1', 0),
                answers.get('q2', 0),
                answers.get('q3', 0),
                answers.get('q4', 0),
                answers.get('q5', 0),
                answers.get('q6', 0)
            ))
            conn.commit()
    except Exception as e:
        logger.error(f"Error saving evening audit: {e}")

# ==================== СИСТЕМА НАЧИСЛЕНИЯ ОЧКОВ ====================
async def award_points(user_id: int, action: str, message: types.Message = None):
    """Начислить очки и уведомить пользователя"""
    global gamification
    
    try:
        result = gamification.add_points(user_id, action)
        
        if 'error' in result:
            return
        
        if result['points_added'] != 0 and message:
            points_text = f"+{result['points_added']} ⭐"
            
            if result.get('new_title'):
                await message.answer(
                    f"🎉 **ПОВЫШЕНИЕ!**\n\n"
                    f"Ты достиг(ла) звания:\n"
                    f"{result['new_title']['emoji']} **{result['new_title']['name']}**\n"
                    f"{result['new_title']['desc']}"
                )
            
            if result.get('new_achievements'):
                for ach in result['new_achievements']:
                    await message.answer(
                        f"🏆 **НОВОЕ ДОСТИЖЕНИЕ!**\n"
                        f"{ach['emoji']} {ach['name']}\n"
                        f"{ach['desc']}\n"
                        f"+{ach['points']} ⭐"
                    )
            
            if not result.get('new_title') and not result.get('new_achievements'):
                await message.answer(f"✨ {points_text} очков биохакера!")
    
    except Exception as e:
        logger.error(f"Error awarding points: {e}")



# ==================== МАШИНА СОСТОЯНИЙ ====================
class Reg(StatesGroup):
    real_name = State()
    power_name = State()
    gender = State()
    goal = State()
    age = State()
    rest_confirmation = State()
    cycle_start = State()
    cycle_length = State()
    work_type = State()
    hiit_choice = State()
    tz = State()
    wake_time = State()
    body_params = State()
    body_params_extra = State()
    birth_date = State()
    genetics_consent = State()
    genetics_mthfr = State()
    genetics_fto = State()
    genetics_actn3 = State() 
    genetics_file_upload = State()
    water_settings = State()
    water_log = State()      

class Morning(StatesGroup):
    sleep_quality = State()
    pulse_lie = State()
    pulse_stand = State()

class Evening(StatesGroup):
    q1 = State()
    q2 = State()
    q3 = State()
    q4 = State()
    q5 = State()
    q6 = State()   
    
class AIState(StatesGroup):
    waiting = State()    
    
# ==================== ЛОГИКА РАСЧЕТОВ ====================
def get_daily_protocol(user: Dict[str, Any]) -> str:
    """Получить персональную рекомендацию с учетом всех циклов"""
    if not user:
        return "❌ Пользователь не найден"
    
    # ЭТА СТРОКА ДОЛЖНА БЫТЬ ИМЕННО ТАК
    today = date.today()
    
    # Получаем день ЦНС
    rhythm_start = date.fromisoformat(user['rhythm_start'])
    cns_day = (today - rhythm_start).days % 9 + 1
    cns_data = get_cns_phase(cns_day)
    
    # Базовая информация
    result = f"🧬 **{user.get('power_name', '')}, твой статус на сегодня:**\n\n"
    result += f"🧠 **ЦНС:** День {cns_day} — {cns_data['name']}\n"
    result += f"📊 {cns_data['desc']}\n\n"
    
    # Переменные для других блоков
    female_day = None
    hiit_allowed = True
    
    # Женский цикл
    if user.get('gender_type') == 1:
        cycle_start = date.fromisoformat(user['cycle_start'])
        cycle_length = user.get('cycle_length', 28)
        female_day = (today - cycle_start).days % cycle_length + 1
        female_data = get_female_phase(female_day, cycle_length)
        
        result += f"🩸 **Цикл:** {female_data['name']} (День {female_day})\n"
        result += f"📋 {female_data['description']}\n\n"
                
        rec = get_combined_recommendation(female_day, cns_day, cycle_length)
        result += f"💪 **РЕКОМЕНДАЦИЯ:**\n{rec['load']}\n\n"
        result += f"🥗 **ПИТАНИЕ:**\n{rec['nutrition']}\n"
        if rec.get('hormones'):
            result += f"🧪 **ГОРМОНЫ:**\n{rec['hormones']}\n"
        
        # Проверяем, можно ли делать HIIT по дням цикла
        if 1 <= female_day <= 5 or 25 <= female_day <= 28:
            hiit_allowed = False
            
    else:
        if user.get('gender_type') == 2:
            result += f"💪 **НАГРУЗКА:** {cns_data['load']}\n"
            result += f"🌸 **СПЕЦПРОТОКОЛ (менопауза):**\n"
            result += f"• Калий: авокадо, курага, зелень\n"
            result += f"• Силовые вместо прыжков\n"
            result += f"• Кальций + D3 + K2\n\n"
        else:
            result += f"💪 **НАГРУЗКА:** {cns_data['load']}\n"   
            
        # Проверяем день ЦНС - День 9 (Тишина) - полный отдых
    if cns_day == 9:
        hiit_allowed = False
    
    
        # Проверяем пульс (с защитой от None)
    last_delta = user.get('last_pulse_delta')
    if last_delta is not None and last_delta > 20:
        hiit_allowed = False
    
    # ==== ДЕТАЛЬНЫЕ РЕКОМЕНДАЦИИ ====
    result += "\n🌅 **УТРЕННИЙ ПРОТОКОЛ:**\n"
    result += "• 💧 Стакан горячей воды с лимоном/псиллиумом\n"
    result += "• 🧘 Лимфодренаж (прыжки/тараканчик)\n"
    result += "• 🤸‍♀️ Йога / разминка суставов\n\n"
    
    result += "🥑 **ЗАВТРАК (через 1.5 часа):**\n"
    result += "• Белки + Жиры (омлет, авокадо, рыба)\n"
    result += "• 💊 БАДы: Д3, Омега\n"
    result += "• ❌ Никаких каш и сахара\n\n"
    
    # HIIT рекомендация
    if hiit_allowed:
        result += "⚡ **HIIT (11:00):** Разрешена интенсивная тренировка\n"
    else:
        result += "🧘 **HIIT (11:00):** Сегодня легкая активность, прогулка\n"
    
    result += "\n🥗 **ОБЕД (13:00):** Самый плотный прием пищи\n"
    result += "🍖 Белок + 🍚 Сложные углеводы + 🥗 Клетчатка\n\n"
    
    result += "🌱 **УЖИН (18:00):** Только растительная пища\n"
    result += "• Стоп животный белок\n"
    result += "• 💊 Магний\n\n"
    
    result += "😴 **СОН (22:00):** Гаджеты в сторону\n\n"
    
    return result

# ==================== ПЛАНИРОВЩИК ====================
async def send_reminder(user_id: int, text: str):
    try:
        await bot.send_message(user_id, text)
        logger.info(f"Reminder sent to user {user_id}")
    except Exception as e:
        logger.error(f"Failed to send message to {user_id}: {e}")

async def send_hiit_reminder(user_id: int):
    user = get_user(user_id)
    if not user:
        return
    
    kb = InlineKeyboardBuilder()
    kb.button(text=BotTexts.HIIT_DONE_BUTTON, callback_data="hiit_done")
    kb.button(text=BotTexts.HIIT_SKIP_BUTTON, callback_data="hiit_skip")
    
    await bot.send_message(
        user_id, 
        "⚡ **Время HIIT!** Пора размяться!",
        reply_markup=kb.as_markup()
    )

async def send_daily_protocol(user_id: int):
    """Отправить дневной протокол"""
    user = get_user(user_id)
    if user:
        # Добавляем проверку времени перед отправкой
        now = datetime.now()
        print(f"📤 Отправляю дневной протокол пользователю {user_id} в {now}")
        
        await bot.send_message(user_id, get_daily_protocol(user))
        await bot.send_message(user_id, "Нажми '🚀 Я проснулся' для утреннего опроса")

async def send_evening_reminder(user_id: int):
    """Отправить напоминание о вечернем опросе и начать опрос"""
    user = get_user(user_id)
    if not user:
        return
    
    # Отправляем приглашение
    await bot.send_message(
        user_id, 
        BotTexts.EVENING_REMINDER.format(name=user['power_name'])
    )
    
    # Начинаем опрос через состояние
    await bot.send_message(
        user_id,
        BotTexts.AUDIT_INTRO
    )
    await bot.send_message(
        user_id,
        BotTexts.AUDIT_QUESTIONS[0]
    )
    
    # Устанавливаем состояние для пользователя
    # Для этого нужно получить доступ к FSM через диспетчер
    state = dp.fsm.get_context(bot=bot, user_id=user_id, chat_id=user_id)
    await state.set_state(Evening.q1)

async def send_break_reminder(user_id: int):
    user = get_user(user_id)
    if user:
        await bot.send_message(user_id, random.choice(BotTexts.WORK_BREAK).format(name=user['power_name']))

async def send_cheat_reminder(user_id: int):
    await bot.send_message(user_id, BotTexts.CHEAT_REMINDER)

async def send_water_reminder(user_id: int, meal: str):
    """Отправить напоминание о воде перед едой"""
    texts = {
        "breakfast": BotTexts.WATER_REMINDER_BREAKFAST,
        "lunch": BotTexts.WATER_REMINDER_LUNCH,
        "dinner": BotTexts.WATER_REMINDER_DINNER
    }
    
    kb = InlineKeyboardBuilder()
    kb.button(text=BotTexts.BTN_WATER_DONE, callback_data=f"water_done_{meal}")
    
    await bot.send_message(
        user_id,
        texts.get(meal, "💧 Не забудь выпить стакан воды!"),
        reply_markup=kb.as_markup()
    )

async def setup_user_schedule(user_id: int):
    user = get_user(user_id)
    if not user:
        return
    
    for job in scheduler.get_jobs():
        if job.id and job.id.startswith(f"user_{user_id}_"):
            job.remove()
    
    tz_info = pytz.timezone(user['tz'])
    wake_time = datetime.strptime(user['wake_time'], '%H:%M').time()
    
    # 👇 ВЕСЬ ЭТОТ БЛОК ДОЛЖЕН БЫТЬ С ОДИНАКОВЫМ ОТСТУПОМ
    # Утренний протокол
    scheduler.add_job(
        send_daily_protocol,
        CronTrigger(hour=wake_time.hour, minute=wake_time.minute, timezone=tz_info),
        args=[user_id],
        id=f"user_{user_id}_morning"
    )
    
    # Добавляем логирование для отладки
    print(f"⏰ Для пользователя {user_id} установлено время пробуждения: {wake_time} в часовом поясе {user['tz']}")
    
    # Завтрак 8:30
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=8, minute=30, timezone=tz_info),
        args=[user_id, "🍳 **ЗАВТРАК (8:30)**\n• Белки + Жиры\n• БАДы: Д3, Омега\n• ❌ Никаких каш и сахара"],
        id=f"user_{user_id}_breakfast"
    )
    
    # ПИК МЕНТАЛЬНОЙ АКТИВНОСТИ
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=9, minute=30, timezone=tz_info),
        args=[user_id, "🧠 **ПИК МЕНТАЛЬНОЙ АКТИВНОСТИ**\n• Решай сложные задачи"],
        id=f"user_{user_id}_mental_peak"
    )
    
    # HIIT
    hiit_hour = 11
    if user.get('hiit_time'):
        hiit_hour = int(user['hiit_time'].split(':')[0])
    
    scheduler.add_job(
        send_hiit_reminder,
        CronTrigger(hour=hiit_hour, minute=0, timezone=tz_info),
        args=[user_id],
        id=f"user_{user_id}_hiit"
    )
    
    # Обед 13:30
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=13, minute=30, timezone=tz_info),
        args=[user_id, "🥗 **ОБЕД (13:30)**\n• Самый плотный прием пищи"],
        id=f"user_{user_id}_lunch"
    )
    
    # Щелочной детокс
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=15, minute=0, timezone=tz_info),
        args=[user_id, "💧 **ЩЕЛОЧНОЙ ДЕТОКС**\n• Пьем щелочную воду"],
        id=f"user_{user_id}_alkaline"
    )
    
    # Ужин 17:30
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=17, minute=30, timezone=tz_info),
        args=[user_id, "🌱 **УЖИН (17:30)**\n• Только растительная пища\n• 💊 Магний"],
        id=f"user_{user_id}_dinner"
    )
    
    # Напоминания о воде за 30 минут до еды
    scheduler.add_job(
        send_water_reminder,
        CronTrigger(hour=8, minute=0, timezone=tz_info),
        args=[user_id, "breakfast"],
        id=f"user_{user_id}_water_breakfast"
    )
    
    scheduler.add_job(
        send_water_reminder,
        CronTrigger(hour=13, minute=0, timezone=tz_info),
        args=[user_id, "lunch"],
        id=f"user_{user_id}_water_lunch"
    )
    
    scheduler.add_job(
        send_water_reminder,
        CronTrigger(hour=17, minute=0, timezone=tz_info),
        args=[user_id, "dinner"],
        id=f"user_{user_id}_water_dinner"
    )
    
    # Уход за телом
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=19, minute=30, timezone=tz_info),
        args=[user_id, "🛁 **УХОД ЗА ТЕЛОМ**\n• Теплая ванна\n• Уход за кожей"],
        id=f"user_{user_id}_body_care"
    )
    
    # Время тишины
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=20, minute=0, timezone=tz_info),
        args=[user_id, "🧘 **ВРЕМЯ ТИШИНЫ**\n• Йога/дыхание\n• 📵 Гаджеты в сторону"],
        id=f"user_{user_id}_antistress"
    )
    
    # Вечерний опрос
    scheduler.add_job(
        send_evening_reminder,
        CronTrigger(hour=21, minute=0, timezone=tz_info),
        args=[user_id],
        id=f"user_{user_id}_audit"
    )
    
    # Отбой
    scheduler.add_job(
        send_reminder,
        CronTrigger(hour=22, minute=30, timezone=tz_info),
        args=[user_id, "😴 **ВРЕМЯ СНА**\n• Гаджеты выключены\n• Спи"],
        id=f"user_{user_id}_sleep"
    )

async def setup_all_schedules():
    users = get_all_users()
    if users:
        for user in users:
            await setup_user_schedule(user['user_id'])
        logger.info(f"Schedules setup for {len(users)} users")

# ==================== ФУНКЦИЯ ГЕНЕТИЧЕСКОГО ОТЧЕТА ====================
def generate_genetics_report(mthfr_genotype, fto_genotype, actn3_genotype):
    """Генерирует отчет на основе генотипов"""
    
    # Интерпретация MTHFR
    mthfr_result = "❓ Не определено"
    if mthfr_genotype in ['CC', 'C/C', '✅ Норма (C/C)']:
        mthfr_result = "✅ Норма — фолатный цикл работает нормально"
    elif mthfr_genotype in ['CT', 'C/T', '⚠️ Гетерозигота (C/T)']:
        mthfr_result = "⚠️ Гетерозигота — активность MTHFR снижена на 30-40%"
    elif mthfr_genotype in ['TT', 'T/T', '🔴 Гомозигота (T/T)']:
        mthfr_result = "🔴 Гомозигота — активность MTHFR снижена на 70%"
    
    # Интерпретация FTO
    fto_result = "❓ Не определено"
    if fto_genotype in ['TT', 'T/T', '✅ TT — нормальный риск']:
        fto_result = "✅ Нормальный риск ожирения"
    elif fto_genotype in ['AT', 'A/T', '⚠️ AT — повышенный риск']:
        fto_result = "⚠️ Повышенный риск (+20% к ИМТ)"
    elif fto_genotype in ['AA', 'A/A', '🔴 AA — высокий риск']:
        fto_result = "🔴 Высокий риск (на 280 ккал/день больше)"
    
    # Интерпретация ACTN3
    actn3_result = "❓ Не определено"
    if actn3_genotype in ['RR', 'RX', 'R/R', 'R/X', '💪 Взрывной тип (RR/RX)']:
        actn3_result = "💪 Взрывной тип (быстрые мышечные волокна)"
    elif actn3_genotype in ['XX', 'X/X', '🏃 Выносливый тип (XX)']:
        actn3_result = "🏃 Выносливый тип (медленные мышечные волокна)"
    
    # Формируем отчет
    report = f"""🧬 **Твой генетический профиль (из файла):**

**MTHFR:** {mthfr_result}
**FTO:** {fto_result}
**ACTN3:** {actn3_result}

📋 **Персональные рекомендации:**

"""
    
    # Добавляем рекомендации по MTHFR
    if 'Гомозигота' in mthfr_result:
        report += "• Метилфолат 800-1000 мкг/день + B12 1000 мкг/день\n"
    elif 'Гетерозигота' in mthfr_result:
        report += "• Метилфолат 400-800 мкг/день\n"
    
    # Добавляем рекомендации по FTO
    if 'Высокий' in fto_result:
        report += "• Критически важно: 150+ мин физ. активности в неделю\n"
        report += "• Белок 30г на завтрак, клетчатка перед едой\n"
    elif 'Повышенный' in fto_result:
        report += "• Контроль порций, белковый завтрак\n"
        report += "• 10 000 шагов в день\n"
    
    # Добавляем рекомендации по ACTN3
    if 'Взрывной' in actn3_result:
        report += "• Силовые тренировки 3-4 раза в неделю\n"
        report += "• HIIT, спринт, взрывные нагрузки\n"
    elif 'Выносливый' in actn3_result:
        report += "• Бег, плавание, велосипед\n"
        report += "• Длительные аэробные нагрузки\n"
    
    report += "\n⚠️ *Рекомендации требуют консультации с врачом.*"
    
    return report


# ==================== ХЭНДЛЕРЫ РЕГИСТРАЦИИ ====================
#временная команда, после теста удалить
@dp.message(Command("test_id"))
async def test_id(message: types.Message):
    """Тест ID"""
    text = f"""
📊 **ТЕСТ ID**
👤 from_user.id: {message.from_user.id}
💬 chat.id: {message.chat.id}
    """
    await message.answer(text)



@dp.message(Command("start"))
@dp.message(Command("register"))
async def cmd_start(message: types.Message, state: FSMContext):
    if not check_registration_spam(message.from_user.id):
        return await message.answer(
            "⏳ Слишком много попыток регистрации. Попробуй через час."
        )
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    
    await message.answer(BotTexts.WELCOME, reply_markup=types.ReplyKeyboardRemove())
    await state.set_state(Reg.real_name)

@dp.message(Command("buy"))
async def buy_subscription(message: types.Message):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    """Показать тарифы для покупки"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    # Создаем клавиатуру с тарифами
    kb = InlineKeyboardBuilder()
    kb.button(text=BotTexts.BUY_CORE, callback_data="buy_core")
    kb.button(text=BotTexts.BUY_VIP, callback_data="buy_vip")
    kb.button(text=BotTexts.BUY_CORE_YEAR, callback_data="buy_core_year")
    kb.button(text=BotTexts.BUY_VIP_YEAR, callback_data="buy_vip_year")
    kb.adjust(2)
    
    await message.answer(
        BotTexts.BUY_INTRO + "\n\n" + BotTexts.BUY_PROMO,
        reply_markup=kb.as_markup()
    )
    
@dp.callback_query(F.data.startswith("buy_"))
async def buy_callback(callback: types.CallbackQuery):
    """Обработка выбора тарифа"""
    tariff = callback.data
    
    # Описание тарифа
    descriptions = {
        "buy_core": BotTexts.BUY_CORE_DESC,
        "buy_vip": BotTexts.BUY_VIP_DESC,
        "buy_core_year": BotTexts.BUY_CORE_DESC + "\n\n📅 **Годовая подписка** — экономия 45%",
        "buy_vip_year": BotTexts.BUY_VIP_DESC + "\n\n📅 **Годовая подписка** — экономия 37%"
    }
    
    # Цены (в рублях)
    prices = {
        "buy_core": 1490,
        "buy_vip": 3990,
        "buy_core_year": 9900,
        "buy_vip_year": 29900
    }
    
    text = descriptions.get(tariff, "") + f"\n\n💰 **Цена:** {prices.get(tariff)}₽\n\nОплата разовая, доступ навсегда."
    
    # Кнопки подтверждения
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ Подтвердить оплату", callback_data=f"pay_{tariff}")
    kb.button(text="◀️ Назад", callback_data="back_to_buy")
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()
    
@dp.callback_query(F.data == "back_to_buy")
async def back_to_buy(callback: types.CallbackQuery):
    """Вернуться к выбору тарифа"""
    kb = InlineKeyboardBuilder()
    kb.button(text=BotTexts.BUY_CORE, callback_data="buy_core")
    kb.button(text=BotTexts.BUY_VIP, callback_data="buy_vip")
    kb.button(text=BotTexts.BUY_CORE_YEAR, callback_data="buy_core_year")
    kb.button(text=BotTexts.BUY_VIP_YEAR, callback_data="buy_vip_year")
    kb.adjust(2)
    
    await callback.message.edit_text(
        BotTexts.BUY_INTRO + "\n\n" + BotTexts.BUY_PROMO,
        reply_markup=kb.as_markup()
    )
    await callback.answer()
    
@dp.callback_query(F.data.startswith("pay_"))
async def pay_callback(callback: types.CallbackQuery):
    """Подтверждение оплаты (сейчас просто тест)"""
    tariff = callback.data.replace("pay_", "")
    
    # Словарь соответствия тарифов и названий
    tariff_names = {
        "buy_core": "CORE",
        "buy_vip": "VIP",
        "buy_core_year": "CORE (год)",
        "buy_vip_year": "VIP (год)"
    }
    
    # Здесь будет интеграция с платежной системой
    # Пока просто тест - сразу активируем
    
    # Определяем срок подписки
    from datetime import datetime, timedelta
    today = datetime.now().date()
    
    if "year" in tariff:
        until = today + timedelta(days=365)
        status = "core" if "core" in tariff else "vip"
    else:
        until = today + timedelta(days=30)
        status = "core" if "core" in tariff else "vip"
    
    # Обновляем статус в БД
    update_user_db(callback.from_user.id, {
        'subscription_status': status,
        'subscription_until': until.isoformat()
    })
    
    # Поздравляем с покупкой
    await callback.message.edit_text(
        BotTexts.BUY_SUCCESS.format(tariff=tariff_names.get(tariff, "CORE"))
    )
    
    # Отправляем приветственное сообщение
    await callback.message.answer(
        "🎁 **Что дальше?**\n\n"
        "Теперь тебе доступны все функции твоего тарифа.\n"
        "Просто продолжай пользоваться ботом — всё разблокируется автоматически!"
    )
    
    await callback.answer("✅ Доступ активирован!")
    
    
    

@dp.message(Reg.real_name)
async def process_real_name(message: types.Message, state: FSMContext):
    # 1. Сначала проверяем на мат
    if profanity.contains_profanity(message.text):
        return await message.answer(
            "🚫 Пожалуйста, используй литературные выражения."
        )
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    
    # 2. Если всё чисто, продолжаем
    await state.update_data(real_name=message.text)
    await message.answer(BotTexts.POWER_NAME)
    await state.set_state(Reg.power_name)

@dp.message(Reg.power_name)
async def process_power_name(message: types.Message, state: FSMContext):
    # Проверка на мат
    if profanity.contains_profanity(message.text):
        return await message.answer(
            "🚫 Пожалуйста, используй литературные выражения."
        )
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    
    # Проверка длины
    if len(message.text) < 2 or len(message.text) > 30:
        return await message.answer(
            "❓ Имя силы должно быть от 2 до 30 символов. Попробуй еще раз."
        )
    
    await state.update_data(power_name=message.text)
    
    kb = ReplyKeyboardBuilder()
    for opt in BotTexts.GENDER_OPTIONS:
        kb.button(text=opt)
    
    await message.answer(BotTexts.GENDER_PROMPT, reply_markup=kb.adjust(1).as_markup(resize_keyboard=True))
    await state.set_state(Reg.gender)

@dp.message(Reg.gender, F.text.in_(BotTexts.GENDER_OPTIONS))
async def process_gender(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    gender_map = {
        BotTexts.GENDER_OPTIONS[0]: 1,
        BotTexts.GENDER_OPTIONS[1]: 2,
        BotTexts.GENDER_OPTIONS[2]: 3
    }
    await state.update_data(gender_type=gender_map[message.text])

    
    
    # ПОКАЗЫВАЕМ ВЫБОР ЦЕЛИ
    kb = ReplyKeyboardBuilder()
    for opt in BotTexts.GOAL_OPTIONS:
        kb.button(text=opt)
    
    await message.answer(
        BotTexts.GOAL_PROMPT,
        reply_markup=kb.adjust(1).as_markup(resize_keyboard=True)
    )
    await state.set_state(Reg.goal)

@dp.message(Reg.birth_date)
async def process_birth_date(message: types.Message, state: FSMContext):
    """Обработка даты рождения и расчет возраста"""
    try:
        date_obj = datetime.strptime(message.text, "%d.%m.%Y").date()
        today = date.today()
        age = today.year - date_obj.year - ((today.month, today.day) < (date_obj.month, date_obj.day))
        
        await state.update_data(birth_date=date_obj.isoformat(), age=age)
        
        # ... дальше по логике регистрации
    except ValueError:
        await message.answer("❌ Неверный формат. Введи дату в формате ДД.ММ.ГГГГ")


@dp.message(Reg.goal, F.text.in_(BotTexts.GOAL_OPTIONS))
async def process_goal(message: types.Message, state: FSMContext):
    # Сохраняем цель
    goal_map = {
        BotTexts.GOAL_OPTIONS[0]: "weight_loss",
        BotTexts.GOAL_OPTIONS[1]: "rejuvenation",
        BotTexts.GOAL_OPTIONS[2]: "brain_health"
    }
    await state.update_data(goal=goal_map[message.text])
    
    # 👇 ЗАПРАШИВАЕМ ВОЗРАСТ
    await message.answer(
        "🎂 **Сколько тебе полных лет?**\n\n"
        "Это поможет точнее рассчитать твой энергетический прогноз.\n\n"
        "Введи число (например: 35, 42, 51):",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Reg.age)


@dp.message(Reg.rest_confirmation, F.text.in_(["✅ Да, я готов(а)", "❌ Нет, напомни позже"]))
async def process_rest_confirmation(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if "✅ Да" in message.text:
        await message.answer("Отлично! Тогда продолжаем регистрацию.")
        kb = ReplyKeyboardBuilder()
        for opt in BotTexts.WORK_TYPE_OPTIONS:
            kb.button(text=opt)
        await message.answer(
            BotTexts.WORK_TYPE_PROMPT.format(name=(await state.get_data())['power_name']),
            reply_markup=kb.adjust(1).as_markup(resize_keyboard=True)
        )
        await state.set_state(Reg.work_type)
    else:
        await message.answer("Хорошо, я напомню позже. Напиши /start когда будешь готов(а).")
        await state.clear()


@dp.message(Reg.cycle_start)
async def process_cycle_start(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    try:
        date_obj = datetime.strptime(message.text, "%d.%m.%Y").date()
        await state.update_data(cycle_start=date_obj.isoformat())
        await message.answer(BotTexts.CYCLE_LENGTH_PROMPT)
        await state.set_state(Reg.cycle_length)
    except ValueError:
        await message.answer(BotTexts.ERROR_FORMAT_DATE)


@dp.message(Reg.cycle_length)
async def process_cycle_length(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 20 < int(message.text) < 40:
        await state.update_data(cycle_length=int(message.text))
        data = await state.get_data()
        kb = ReplyKeyboardBuilder()
        for opt in BotTexts.WORK_TYPE_OPTIONS:
            kb.button(text=opt)
        await message.answer(
            BotTexts.WORK_TYPE_PROMPT.format(name=data['power_name']),
            reply_markup=kb.adjust(1).as_markup(resize_keyboard=True)
        )
        await state.set_state(Reg.work_type)
    else:
        await message.answer(BotTexts.ERROR_FORMAT_INT)

@dp.message(Reg.age)
async def process_age(message: types.Message, state: FSMContext):
    """Обработка возраста"""
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    
    # Проверяем, что ввели число
    if not message.text.isdigit():
        return await message.answer("❌ Пожалуйста, введи число (только цифры)")
    
    age = int(message.text)
    
    # Проверяем разумные пределы
    if age < 12 or age > 120:
        return await message.answer("❌ Пожалуйста, введи реальный возраст (от 12 до 120 лет)")
    
    await state.update_data(age=age)
    
    # Дальше идем по логике регистрации
    data = await state.get_data()
    
    if data.get('gender_type') == 1:
        # женщина с циклом
        await message.answer(BotTexts.CYCLE_PROMPT, reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Reg.cycle_start)
    else:
        # женщина без цикла или мужчина
        kb = ReplyKeyboardBuilder()
        kb.button(text="✅ Да, я готов(а)")
        kb.button(text="❌ Нет, напомни позже")
        await message.answer(
            BotTexts.REST_WARNING,
            reply_markup=kb.adjust(1).as_markup(resize_keyboard=True)
        )
        await state.set_state(Reg.rest_confirmation)

@dp.message(Reg.work_type, F.text.in_(BotTexts.WORK_TYPE_OPTIONS))
async def process_work_type(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
        
    await state.update_data(work_type=message.text)
    data = await state.get_data()
    
    if data.get('gender_type') == 1 and message.text == "💻 Офис (сидячая работа)":
        kb = ReplyKeyboardBuilder()
        for opt in BotTexts.HIIT_OPTIONS:
            kb.button(text=opt)
        await message.answer(BotTexts.HIIT_OFFICE_PROMPT, reply_markup=kb.adjust(2).as_markup(resize_keyboard=True))
        await state.set_state(Reg.hiit_choice)
    else:
        kb = ReplyKeyboardBuilder()
        for opt in BotTexts.TZ_OPTIONS:
            kb.button(text=opt)
        await message.answer(
            BotTexts.TZ_PROMPT,
            reply_markup=kb.adjust(1).as_markup(resize_keyboard=True)
        )
        await state.set_state(Reg.tz)


@dp.message(Reg.hiit_choice)
async def process_hiit_choice(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    """Обработка выбора времени HIIT"""
    print(f"🔍 Выбрано: {message.text}")
    
    # Принимаем любой текст, но пытаемся распознать
    if "11:00" in message.text:
        await state.update_data(hiit_time="11:00")
        print("✅ Установлено 11:00")
    elif "16:00" in message.text:
        await state.update_data(hiit_time="16:00")
        print("✅ Установлено 16:00")
    else:
        await state.update_data(hiit_time=None)
        print("✅ Установлено None (нет HIIT)")
    
    # 👇 ВАЖНО: СОЗДАЕМ КЛАВИАТУРУ С ЧАСОВЫМИ ПОЯСАМИ
    kb = ReplyKeyboardBuilder()
    for opt in BotTexts.TZ_OPTIONS:
        kb.button(text=opt)
    
    # 👇 ОТПРАВЛЯЕМ С КЛАВИАТУРОЙ
    await message.answer(
        BotTexts.TZ_PROMPT,
        reply_markup=kb.adjust(1).as_markup(resize_keyboard=True)
    )
    await state.set_state(Reg.tz)
    print("➡️ Переход к выбору часового пояса")

@dp.message(Reg.tz)
async def process_timezone(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text in BotTexts.TZ_OPTIONS:
        tz_value = BotTexts.TZ_MAPPING[message.text]
        await state.update_data(tz=tz_value)
        await message.answer(BotTexts.WAKE_TIME_PROMPT, reply_markup=types.ReplyKeyboardRemove())
        await state.set_state(Reg.wake_time)
    else:
        kb = ReplyKeyboardBuilder()
        for opt in BotTexts.TZ_OPTIONS:
            kb.button(text=opt)
        
        await message.answer(
            BotTexts.TZ_PROMPT,
            reply_markup=kb.adjust(1).as_markup(resize_keyboard=True)
        )

@dp.message(Reg.wake_time)
async def process_wake_time(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if re.match(r'^([0-1]?[0-9]|2[0-3])\.[0-5][0-9]$', message.text):
        time_with_colon = message.text.replace('.', ':')
        await state.update_data(wake_time=time_with_colon)
        await message.answer(BotTexts.BODY_PARAMS_PROMPT)  # ИСПРАВЛЕНО
        await state.set_state(Reg.body_params)  # ИСПРАВЛЕНО
    else:
        await message.answer(BotTexts.ERROR_FORMAT_TIME)



@dp.message(Reg.body_params)
async def process_body_params(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    parts = message.text.split()
    if len(parts) == 3 and all(p.replace('.', '').isdigit() for p in parts):
        weight, waist, hips = map(float, parts)
        await state.update_data(weight=weight, waist=waist, hips=hips)
        await message.answer(BotTexts.BODY_PARAMS_EXTRA)
        await state.set_state(Reg.body_params_extra)
    else:
        await message.answer(BotTexts.ERROR_FORMAT_NUMBERS)

@dp.message(Reg.body_params_extra)
async def finish_registration(message: types.Message, state: FSMContext):
    data = await state.get_data()
    today = date.today()
    
    # 👇 ПРОВЕРЬ, ЧТО ВСЕ ПОЛЯ ЗАПОЛНЕНЫ
    required_fields = ['real_name', 'power_name', 'wake_time', 'tz']
    for field in required_fields:
        if field not in data:
            print(f"❌ Ошибка: отсутствует поле {field}")
            await message.answer("❌ Ошибка регистрации. Начни заново: /start")
            await state.clear()
            return
    
    if data.get('gender_type') == 1:
        if 'cycle_start' in data:
            cycle_start = date.fromisoformat(data['cycle_start'])
            rhythm_start = cycle_start + timedelta(days=5)
        else:
            rhythm_start = today
    else:
        days_to_monday = (today.weekday()) % 7
        rhythm_start = today - timedelta(days=days_to_monday)
    
    user_data = {
        'real_name': data['real_name'],
        'power_name': data['power_name'],
        'gender_type': data['gender_type'],
        'age': data.get('age', 30),
        'work_type': data.get('work_type', ''),
        'hiit_time': data.get('hiit_time', ''),
        'wake_time': data['wake_time'],
        'tz': data['tz'],
        'rhythm_start': rhythm_start.isoformat(),
        'cycle_start': data.get('cycle_start', today.isoformat()),
        'cycle_length': data.get('cycle_length', 28),
        'weight': data.get('weight', 0),
        'waist': data.get('waist', 0),
        'hips': data.get('hips', 0),
        'chest': data.get('chest', 0),
        'resting_hr': data.get('resting_hr', 0),
        'registered_date': today.isoformat(),
        'bio_points': 0,
        'achievements': '[]',
        'streak_days': 0,
        'last_activity': today.isoformat(),
        'goal': data.get('goal', 'weight_loss'),
        'water_goal': 2000,
        'water_consumed_today': 0,
        'water_preferences': '{}',
        'subscription_status': 'free'       
    }
    
    # 👇 ЭТА СТРОКА ДОЛЖНА БЫТЬ
    add_user(message.from_user.id, user_data)
    
    # 👇 ПРОВЕРКА, ЧТО ПОЛЬЗОВАТЕЛЬ СОХРАНИЛСЯ
    test_user = get_user(message.from_user.id)
    if test_user:
        print(f"✅ Пользователь {message.from_user.id} сохранен: {test_user['power_name']}")
    else:
        print(f"❌ Ошибка: пользователь {message.from_user.id} НЕ сохранился!")
    
    await state.clear()
    await setup_user_schedule(message.from_user.id)
    
    from menu import show_main_menu
    await show_main_menu(message)
    
    await award_points(message.from_user.id, "first_blood", message)
    
    user = get_user(message.from_user.id)
    if user:
        await message.answer(get_daily_protocol(user))
    
    
# ==================== ОСНОВНЫЕ ХЭНДЛЕРЫ ====================
@dp.message(Command("menu"))
async def show_menu(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    # ПОКАЗЫВАЕМ НОВОЕ МЕНЮ
    from menu import show_main_menu
    await show_main_menu(message)

@dp.message(Command("resetmenu"))
async def reset_menu(message: types.Message):
    """Принудительно показать меню"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    kb = ReplyKeyboardBuilder()
    for btn in [BotTexts.BTN_WAKE, BotTexts.BTN_PERIODS, BotTexts.BTN_SOS, 
                BotTexts.BTN_WORK, BotTexts.BTN_CHEAT, BotTexts.BTN_PROFILE, 
                BotTexts.BTN_STATS, BotTexts.BTN_AI]:
        kb.button(text=btn)
    
    await message.answer(
        "🔄 Меню восстановлено:", 
        reply_markup=kb.adjust(2).as_markup(resize_keyboard=True)
    )

@dp.message(F.text == BotTexts.BTN_WAKE)
async def wake_up_handler(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    await message.answer(
        BotTexts.WAKE_UP_PROMPT.format(name=user['power_name']),
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Morning.sleep_quality)

@dp.message(Morning.sleep_quality)
async def process_sleep_quality(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 1 <= int(message.text) <= 5:
        await state.update_data(sleep_quality=int(message.text))
        await message.answer(random.choice(BotTexts.PULSE_LIE_PROMPT))
        await state.set_state(Morning.pulse_lie)
    else:
        await message.answer("Пожалуйста, введи число от 1 до 5")

@dp.message(Morning.pulse_lie)
async def process_pulse_lie(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 40 <= int(message.text) <= 120:
        await state.update_data(pulse_lie=int(message.text))
        await message.answer(random.choice(BotTexts.PULSE_STAND_PROMPT))
        await state.set_state(Morning.pulse_stand)
    else:
        await message.answer("Пожалуйста, введи корректное значение пульса (40-120)")

@dp.message(Morning.pulse_stand)
async def process_pulse_stand(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 40 <= int(message.text) <= 140:
        data = await state.get_data()
        pulse_stand = int(message.text)
        delta = pulse_stand - data['pulse_lie']
        
        update_user_db(message.from_user.id, {'last_pulse_delta': delta})
        save_morning_checkin(message.from_user.id, {
            'sleep_quality': data['sleep_quality'],
            'pulse_lie': data['pulse_lie'],
            'pulse_stand': pulse_stand,
            'pulse_delta': delta
        })
        
        # ВАЖНО: очищаем состояние
        await state.clear()
        
        user = get_user(message.from_user.id)
        if delta > 20:
            await message.answer(BotTexts.PULSE_DANGER.format(name=user['power_name']))
        else:
            await message.answer(BotTexts.PULSE_OK)
        
        await award_points(message.from_user.id, "morning_routine", message)
        await message.answer(get_daily_protocol(user))
        
        # ВАЖНО: показываем меню
        kb = ReplyKeyboardBuilder()
        for btn in [BotTexts.BTN_WAKE, BotTexts.BTN_PERIODS, BotTexts.BTN_SOS, 
                    BotTexts.BTN_WORK, BotTexts.BTN_CHEAT, BotTexts.BTN_PROFILE, 
                    BotTexts.BTN_STATS, BotTexts.BTN_GENETICS, BotTexts.BTN_AI]:
            kb.button(text=btn)
        await message.answer(
            "Главное меню:", 
            reply_markup=kb.adjust(2).as_markup(resize_keyboard=True)
        )
    else:
        await message.answer("Пожалуйста, введи корректное значение пульса (40-140)")

@dp.message(Evening.q1)
async def evening_q1(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 1 <= int(message.text) <= 5:
        await state.update_data(q1=int(message.text))
        await message.answer(BotTexts.AUDIT_QUESTIONS[1])
        await state.set_state(Evening.q2)
    else:
        await message.answer("Пожалуйста, введи число от 1 до 5")

@dp.message(Evening.q2)
async def evening_q2(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 1 <= int(message.text) <= 5:
        await state.update_data(q2=int(message.text))
        await message.answer(BotTexts.AUDIT_QUESTIONS[2])
        await state.set_state(Evening.q3)
    else:
        await message.answer("Пожалуйста, введи число от 1 до 5")

@dp.message(Evening.q3)
async def evening_q3(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 1 <= int(message.text) <= 5:
        await state.update_data(q3=int(message.text))
        await message.answer(BotTexts.AUDIT_QUESTIONS[3])
        await state.set_state(Evening.q4)
    else:
        await message.answer("Пожалуйста, введи число от 1 до 5")

@dp.message(Evening.q4)
async def evening_q4(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 1 <= int(message.text) <= 5:
        await state.update_data(q4=int(message.text))
        await message.answer(BotTexts.AUDIT_QUESTIONS[4])
        await state.set_state(Evening.q5)
    else:
        await message.answer("Пожалуйста, введи число от 1 до 5")

@dp.message(Evening.q5)
async def evening_q5(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 1 <= int(message.text) <= 5:
        await state.update_data(q5=int(message.text))
        await message.answer(BotTexts.AUDIT_QUESTIONS[4])
        await state.set_state(Evening.q6)
    else:
        await message.answer("Пожалуйста, введи число от 1 до 5")

@dp.message(Evening.q6)
async def evening_q6(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    if message.text.isdigit() and 1 <= int(message.text) <= 5:
        data = await state.get_data()
        data['q6'] = int(message.text)
        
        # 👇 ПОЛУЧАЕМ ПОЛЬЗОВАТЕЛЯ ИЗ БАЗЫ
        user = get_user(message.from_user.id)
        if not user:
            await message.answer("❌ Ошибка. Начни заново.")
            await state.clear()
            return
        
        # Сохраняем ответы
        save_evening_audit(message.from_user.id, data)
        
        # Начисляем очки
        await award_points(message.from_user.id, "log_filled", message)
        
        # 👇 ТЕПЕРЬ user ОПРЕДЕЛЕН
        await message.answer(BotTexts.AUDIT_COMPLETE.format(name=user['power_name']))
        await state.clear()
        
        # СТАЛО:
        kb = ReplyKeyboardBuilder()
        for btn in [BotTexts.BTN_WAKE, BotTexts.BTN_PERIODS, BotTexts.BTN_SOS, 
                    BotTexts.BTN_WORK, BotTexts.BTN_CHEAT, BotTexts.BTN_PROFILE, 
                    BotTexts.BTN_STATS, BotTexts.BTN_GENETICS, BotTexts.BTN_AI]:
            kb.button(text=btn)
        await message.answer(
            "Главное меню:", 
            reply_markup=kb.adjust(2).as_markup(resize_keyboard=True)
        )
    else:
        await message.answer("Пожалуйста, введи число от 1 до 5")
@dp.message(F.text == BotTexts.BTN_PERIODS)
async def period_reset_handler(message: types.Message):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    if user['gender_type'] != 1:
        return await message.answer("Эта функция доступна только для профиля 'Женщина с циклом'.")
    
    today = date.today()
    new_cycle_start = today.isoformat()
    new_rhythm_start = (today + timedelta(days=5)).isoformat()
    
    update_user_db(message.from_user.id, {
        'cycle_start': new_cycle_start,
        'rhythm_start': new_rhythm_start
    })
    
    await message.answer("✅ Цикл сброшен. Календари синхронизированы.")
    await award_points(message.from_user.id, "cycle_honest", message)
    
    user = get_user(message.from_user.id)
    await message.answer(get_daily_protocol(user))

@dp.message(F.text == BotTexts.BTN_SOS)
async def sos_handler(message: types.Message):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    kb = InlineKeyboardBuilder()
    for opt in BotTexts.SOS_OPTIONS:
        kb.button(text=opt, callback_data=f"sos_{opt}")
    
    await message.answer(BotTexts.SOS_OPTIONS_PROMPT, reply_markup=kb.adjust(1).as_markup())

@dp.callback_query(F.data.startswith("sos_"))
async def sos_option_callback(callback: types.CallbackQuery):
    allowed, msg = await check_rate_limit(callback.from_user.id)
    if not allowed:
        return await callback.message.answer(msg)
    option = callback.data.replace("sos_", "")
    
    if "сладкому" in option:
        text = BotTexts.SOS_SUGAR_CRAVING
    elif "Тревога" in option:
        text = BotTexts.SOS_STRESS
    else:
        text = BotTexts.SOS_FATIGUE
    
    await callback.message.edit_text(text)
    await award_points(callback.from_user.id, "sos_used", callback.message)
    
    kb = InlineKeyboardBuilder()
    kb.button(text=BotTexts.BTN_CALL_PSYCHOLOGIST, callback_data="call_psychologist")
    
    user = get_user(callback.from_user.id)
    await callback.message.answer(
        BotTexts.SOS_PSYCHOLOGIST_PROMPT.format(name=user['power_name'] if user else ''),
        reply_markup=kb.as_markup()
    )
    await callback.answer()

@dp.callback_query(F.data == "call_psychologist")
async def call_psychologist_callback(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        return await callback.answer("Сначала пройди регистрацию", show_alert=True)
    
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO psychologist_calls (user_id, date) 
            VALUES (?, ?)
        """, (callback.from_user.id, datetime.now().isoformat()))
        conn.commit()
    
    await award_points(callback.from_user.id, "sos_pro_used", callback.message)
    
    await bot.send_message(
        ADMIN_ID,
        f"🚨 **ПЛАТНЫЙ ВЫЗОВ ПСИХОЛОГА!**\n\n"
        f"👤 Имя Силы: {user['power_name']}\n"
        f"🆔 ID: {callback.from_user.id}\n"
        f"📝 Настоящее имя: {user['real_name']}"
    )
    
    await callback.message.edit_text(
        "✅ Заявка отправлена! Специалист свяжется с тобой в ближайшее время.\n"
        "Напоминаем: услуга платная (1000 руб/сессия)."
    )
    await callback.answer()

@dp.message(F.text == BotTexts.BTN_WORK)
async def work_mode_handler(message: types.Message):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    await message.answer(random.choice(BotTexts.WORK_START).format(name=user['power_name']))
    await award_points(message.from_user.id, "meditation", message)
    
    scheduler.add_job(
        send_break_reminder,
        'date',
        run_date=datetime.now() + timedelta(minutes=90),
        args=[message.from_user.id],
        id=f"break_{message.from_user.id}_{datetime.now().timestamp()}"
    )

@dp.message(F.text == BotTexts.BTN_STATS)
async def stats_handler(message: types.Message):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT date, sleep_quality, pulse_delta 
            FROM morning_checkin 
            WHERE user_id = ? 
            ORDER BY date DESC LIMIT 7
        """, (message.from_user.id,))
        mornings = cur.fetchall()
        cur.execute("SELECT bio_points FROM users WHERE user_id = ?", (message.from_user.id,))
        points = cur.fetchone()[0]
    
    text = f"📊 **Статистика для {user['power_name']}**\n\n"
    text += f"⭐ **Очки биохакера:** {points}\n\n"
    text += "**Последние 7 дней:**\n"
    
    for m in mornings:
        text += f"📅 {m[0]}: Сон {m[1]}⭐, Пульс {m[2]} дельта\n"
    
    await message.answer(text)

# ==================== AI КОУЧ ====================

@dp.message(F.text == BotTexts.BTN_AI)
async def ai_ask_start(message: types.Message, state: FSMContext):
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    await message.answer(
        "🤖 **Спроси ИИ**\n\n"
        "Задай вопрос о питании, тренировках, циклах:\n"
        "(например: что есть вечером?)"
    )
    await state.set_state(AIState.waiting)


@dp.message(AIState.waiting)
async def ai_ask_process(message: types.Message, state: FSMContext):
    # Проверка на мат
    if profanity.contains_profanity(message.text):
        return await message.answer(
            "🚫 Пожалуйста, задавай вопросы культурно. Это система здоровья."
        )
    
    # Проверка длины вопроса
    if len(message.text) > 500:
        return await message.answer(
            "❓ Слишком длинный вопрос. Пожалуйста, сократи до 500 символов."
        )
    
    await message.answer("🤔 Ищу ответ в базе знаний...")
    
    try:
        if rag is None:
            await message.answer("❌ GigaChat не настроен. Проверь .env файл")
            await state.clear()
            return
        
        response = await rag.ask(message.text)
        await message.answer(f"📚 **Из базы знаний «Код Реверс»:**\n\n{response}")
        
    except Exception as e:
        await message.answer(f"❌ Ошибка: {e}")
    
    await state.clear()
    
    # Показываем меню
    user = get_user(message.from_user.id)
    if user:
        kb = ReplyKeyboardBuilder()
        for btn in [BotTexts.BTN_WAKE, BotTexts.BTN_PERIODS, BotTexts.BTN_SOS, 
                    BotTexts.BTN_WORK, BotTexts.BTN_CHEAT, BotTexts.BTN_PROFILE, 
                    BotTexts.BTN_STATS, BotTexts.BTN_GENETICS, BotTexts.BTN_AI]:
            kb.button(text=btn)
        await message.answer("Главное меню:", reply_markup=kb.adjust(2).as_markup(resize_keyboard=True))

# ==================== КОМАНДА HIIT ====================
@dp.message(Command("hiit"))
async def hiit_command(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    if user['gender_type'] != 1:
        return await message.answer("👨 Эта команда только для женщин с циклом")
    
    from rhythm_core import get_hiit_recommendation
    recommendation = get_hiit_recommendation(user)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🔄 Другой вариант", callback_data="hiit_alternative")
    kb.button(text="📊 Моя статистика", callback_data="my_stats")
    kb.adjust(2)
    
    await message.answer(recommendation, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "hiit_alternative")
async def hiit_alternative(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return
    
    from rhythm_core import get_hiit_protocol, calculate_fat_burn_window
    
    today = date.today()
    cycle_start = date.fromisoformat(user['cycle_start'])
    cycle_length = user.get('cycle_length', 28)
    female_day = (today - cycle_start).days % cycle_length + 1
    
    protocol = get_hiit_protocol(female_day, cycle_length)
    windows = calculate_fat_burn_window(female_day, user['wake_time'])
    
    text = f"🔄 **Альтернативный вариант**\n\n"
    text += f"⏱️ **{protocol['duration']}**\n"
    text += f"💪 **{protocol['type']}**\n\n"
    text += f"⏰ **Другие варианты времени:**\n"
    text += f"1. {windows[1]['time']} - {windows[1]['type']}\n"
    text += f"2. {windows[2]['time']} - {windows[2]['type']}\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад", callback_data="hiit_back")
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "hiit_back")
async def hiit_back(callback: types.CallbackQuery):
    await hiit_command(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "my_stats")
async def my_stats_callback(callback: types.CallbackQuery):
    await stats_handler(callback.message)
    await callback.answer()

@dp.callback_query(F.data == "hiit_done")
async def hiit_done(callback: types.CallbackQuery):
    await award_points(callback.from_user.id, "hiit_done", callback.message)
    await callback.answer("✅ +20 ⭐! Отличная работа!")

@dp.callback_query(F.data == "hiit_skip")
async def hiit_skip(callback: types.CallbackQuery):
    await award_points(callback.from_user.id, "hiit_skip", callback.message)
    await callback.answer("❌ Зафиксировано. В следующий раз получится!")

@dp.callback_query(F.data.startswith("water_done_"))
async def water_done(callback: types.CallbackQuery):
    """Отметить, что вода выпита"""
    meal = callback.data.replace("water_done_", "")
    
    # Начисляем очки
    await award_points(callback.from_user.id, "water_drunk", callback.message)
    
    await callback.message.edit_text(
        f"✅ Отлично! Стакан воды перед {meal}ом выпит. +1 ⭐",
        reply_markup=None
    )
    await callback.answer()

# ==================== КОД СВОБОДА ====================
@dp.message(F.text == BotTexts.BTN_CHEAT)
async def cheat_day_handler(message: types.Message):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    kb = InlineKeyboardBuilder()
    kb.button(text=BotTexts.CHEAT_TODAY, callback_data="cheat_today")
    kb.button(text=BotTexts.CHEAT_TOMORROW, callback_data="cheat_tomorrow")
    kb.button(text=BotTexts.CHEAT_CANCEL, callback_data="cheat_cancel")
    
    await message.answer(BotTexts.CHEAT_PROMPT, reply_markup=kb.as_markup())


@dp.callback_query(F.data == "cheat_cancel")
async def cheat_cancel(callback: types.CallbackQuery):
    await callback.message.edit_text("❌ Отменено. В другой раз!")
    await callback.answer()


# ==================== ОБРАБОТЧИКИ КОДА СВОБОДА ====================

@dp.callback_query(F.data == "cheat_today")
async def cheat_today(callback: types.CallbackQuery):
    """Код Свобода на сегодня"""
    user_id = callback.from_user.id
    
    # Записываем в БД, что сегодня чит-мил
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("UPDATE users SET cheat_day = date('now') WHERE user_id = ?", (user_id,))
        conn.commit()
    
    # Показываем выбор сценария
    kb = InlineKeyboardBuilder()
    kb.button(text=BotTexts.CHEAT_NORMAL, callback_data="cheat_normal")
    kb.button(text=BotTexts.CHEAT_ALCOHOL, callback_data="cheat_alcohol")
    kb.button(text=BotTexts.CHEAT_OVEREAT, callback_data="cheat_overeat")
    kb.button(text=BotTexts.CHEAT_CANCEL, callback_data="cheat_cancel")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "🍕 **Выбери свой сценарий Кода Свобода:**",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "cheat_tomorrow")
async def cheat_tomorrow(callback: types.CallbackQuery):
    """Код Свобода на завтра"""
    user_id = callback.from_user.id
    
    # Планируем на завтра
    scheduler.add_job(
        send_cheat_reminder,
        'date',
        run_date=datetime.now() + timedelta(days=1),
        args=[user_id]
    )
    
    # Показываем выбор сценария
    kb = InlineKeyboardBuilder()
    kb.button(text=BotTexts.CHEAT_NORMAL, callback_data="cheat_normal")
    kb.button(text=BotTexts.CHEAT_ALCOHOL, callback_data="cheat_alcohol")
    kb.button(text=BotTexts.CHEAT_OVEREAT, callback_data="cheat_overeat")
    kb.button(text=BotTexts.CHEAT_CANCEL, callback_data="cheat_cancel")
    kb.adjust(1)
    
    await callback.message.edit_text(
        "🍕 **Выбери свой сценарий Кода Свобода на завтра:**",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@dp.callback_query(F.data == "cheat_normal")
async def cheat_normal(callback: types.CallbackQuery):
    """Обычный чит-мил (без алкоголя)"""
    await callback.message.edit_text(BotTexts.CHEAT_NORMAL_DETAIL)
    await callback.answer()


@dp.callback_query(F.data == "cheat_alcohol")
async def cheat_alcohol(callback: types.CallbackQuery):
    """Чит-мил с алкоголем"""
    await callback.message.edit_text(BotTexts.CHEAT_ALCOHOL_DETAIL)
    await callback.answer()


@dp.callback_query(F.data == "cheat_overeat")
async def cheat_overeat(callback: types.CallbackQuery):
    """Чит-мил при склонности к перееданию"""
    await callback.message.edit_text(BotTexts.CHEAT_OVEREAT_DETAIL)
    await callback.answer()


@dp.callback_query(F.data == "cheat_cancel")
async def cheat_cancel(callback: types.CallbackQuery):
    """Отмена чит-мила"""
    await callback.message.edit_text("❌ Код Свобода отменен. Продолжаем работать над собой!")
    await callback.answer()

async def send_cheat_reminder(user_id: int):
    """Напоминание о запланированном Коде Свобода"""
    try:
        await bot.send_message(user_id, BotTexts.CHEAT_REMINDER)
    except Exception as e:
        logger.error(f"Failed to send cheat reminder to {user_id}: {e}")

# ==================== ХЭНДЛЕРЫ ГЕЙМИФИКАЦИИ ====================
@dp.message(Command("profile"))
@dp.message(F.text == BotTexts.BTN_PROFILE)
async def show_profile(message: types.Message):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    global gamification
    profile_text = gamification.format_profile(message.from_user.id)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🏆 Топ биохамеров", callback_data="leaderboard")
    kb.button(text="🎯 Достижения", callback_data="achievements")
    kb.button(text="🌙 Лунный цикл", callback_data="lunar_info")
    kb.adjust(2)
    
    await message.answer(profile_text, reply_markup=kb.as_markup())

@dp.callback_query(F.data == "leaderboard")
async def show_leaderboard(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден. Напиши /start")
        await callback.answer()
        return
    
    leaders = get_leaderboard(sqlite3.connect(DB_NAME), limit=15)
    
    if not leaders:
        await callback.message.edit_text("Пока нет участников в топе")
        await callback.answer()
        return
    
    text = "🏆 **ТОП БИОХАКЕРОВ**\n\n"
    
    for i, leader in enumerate(leaders, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else "📌"
        text += f"{medal} **{i}.** {leader['emoji']} {leader['name']}\n"
        text += f"   ⭐ {leader['points']} очков | {leader['title']}\n"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад к профилю", callback_data="back_to_profile")
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "achievements")
async def show_achievements(callback: types.CallbackQuery):
    from gamification import ACHIEVEMENTS
    
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден. Напиши /start")
        await callback.answer()
        return
    
    achievements_json = user.get('achievements', '[]')
    try:
        user_achievements = json.loads(achievements_json)
    except:
        user_achievements = []
    
    text = "🏆 **ДОСТИЖЕНИЯ**\n\n"
    text += "🔓 **Открыто:**\n"
    
    opened = 0
    for ach_key in user_achievements:
        if ach_key in ACHIEVEMENTS:
            ach = ACHIEVEMENTS[ach_key]
            if isinstance(ach, dict):
                text += f"{ach.get('emoji', '🏆')} {ach.get('name', ach_key)} (+{ach.get('points', 0)}⭐)\n"
                opened += 1
            else:
                text += f"🏆 {ach_key}\n"
                opened += 1
    
    if opened == 0:
        text += "Пока нет открытых достижений\n"
    
    total = 0
    for ach in ACHIEVEMENTS.values():
        if isinstance(ach, dict) and not ach.get('hidden', False):
            total += 1
        elif not isinstance(ach, dict):
            total += 1
    
    text += f"\n🔒 **Закрыто:** {total - opened}"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="◀️ Назад к профилю", callback_data="back_to_profile")
    
    await callback.message.edit_text(text, reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "back_to_profile")
async def back_to_profile(callback: types.CallbackQuery):
    user = get_user(callback.from_user.id)
    if not user:
        await callback.message.edit_text("❌ Пользователь не найден. Напиши /start")
        await callback.answer()
        return
    
    global gamification
    profile_text = gamification.format_profile(callback.from_user.id)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🏆 Топ биохамеров", callback_data="leaderboard")
    kb.button(text="🎯 Достижения", callback_data="achievements")
    kb.button(text="🌙 Лунный цикл", callback_data="lunar_info")
    kb.adjust(2)
    
    await callback.message.edit_text(profile_text, reply_markup=kb.as_markup())
    await callback.answer()

@dp.callback_query(F.data == "lunar_info")
async def show_lunar_info(callback: types.CallbackQuery):
    """Показать лунный календарь"""
    from lunar import LunarScience, format_lunar_report
    
    lunar = LunarScience()
    data = lunar.get_full_recommendation()
    report = format_lunar_report(data)
    
    await callback.message.edit_text(report)
    await callback.answer()

# ==================== ГЕНЕТИЧЕСКИЙ МОДУЛЬ ====================
@dp.message(Command("genetics"))
@dp.message(F.text == "🧬 Генетика")
async def genetics_start(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    # Проверка доступа для VIP
    if not has_access(message.from_user.id, 'vip'):
        kb = InlineKeyboardBuilder()
        kb.button(text="💳 Купить VIP", callback_data="buy_vip")
        return await message.answer(
            "🧬 **Генетический модуль доступен только в тарифе VIP**\n\n"
            "Купи VIP-доступ и получи:\n"
            "✅ Загрузку PDF генетических тестов\n"
            "✅ Расшифровку 30+ генов\n"
            "✅ Персональные рекомендации по БАДам",
            reply_markup=kb.as_markup()
        )
    
    # Создаем клавиатуру с выбором способа ввода
    kb = InlineKeyboardBuilder()
    kb.button(text="📤 Загрузить файл (авто)", callback_data="genetics_file")
    kb.button(text="✏️ Ввести вручную", callback_data="genetics_manual")
    kb.button(text="⏩ Пропустить", callback_data="genetics_skip")
    
    await message.answer(
        "🧬 **Генетический паспорт здоровья**\n\n"
        "⚠️ **Важно**: Генетика — это предрасположенность, а не приговор.\n\n"
        "Выбери способ ввода данных:",
        reply_markup=kb.as_markup()
    )
    await state.set_state(Reg.genetics_consent)

@dp.callback_query(F.data == "genetics_skip")
async def genetics_skip(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.edit_text("⏩ Генетический модуль пропущен. Можешь вернуться позже через /genetics")
    await state.clear()
    await callback.answer()

@dp.callback_query(F.data == "genetics_manual")
async def genetics_manual(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    
    # MTHFR вопрос
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ Норма (C/C)")
    kb.button(text="⚠️ Гетерозигота (C/T)")
    kb.button(text="🔴 Гомозигота (T/T)")
    kb.adjust(1)
    
    await callback.message.answer(
        "🧬 **Ген MTHFR** (фолатный цикл)\n\n"
        "Выбери свой вариант:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    await state.set_state(Reg.genetics_mthfr)
    await callback.answer()

@dp.callback_query(F.data == "genetics_file")
async def genetics_file_prompt(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    
    await callback.message.answer(
        "📤 **Загрузи файл с результатами генетического теста**\n\n"
        "Поддерживаемые форматы:\n"
        "• CSV из 23andMe, Генотек, MyHeritage\n"
        "• TXT файлы с колонками rsid, chromosome, position, genotype\n\n"
        "Просто отправь файл, и я найду все нужные маркеры!",
        reply_markup=types.ReplyKeyboardRemove()
    )
    await state.set_state(Reg.genetics_file_upload)
    await callback.answer()

@dp.message(Reg.genetics_file_upload, F.document)
async def process_genetics_file(message: types.Message, state: FSMContext):
    # Проверка доступа для VIP
    if not has_access(message.from_user.id, 'vip'):
        await message.answer("❌ Загрузка файлов доступна только в тарифе VIP")
        await state.clear()
        return
    
    await message.answer("🔍 Обрабатываю файл... Это может занять несколько секунд.")
    
    try:
        # 1. Скачиваем файл
        file_id = message.document.file_id
        file = await bot.get_file(file_id)
        file_path = file.file_path
        downloaded_file = await bot.download_file(file_path)
        
        # 2. Читаем содержимое
        content = downloaded_file.read().decode('utf-8', errors='ignore')
        lines = content.splitlines()
        
        # 3. Определяем разделитель (запятая или табуляция)
        first_line = lines[0] if lines else ""
        if ',' in first_line:
            delimiter = ','
        elif '\t' in first_line:
            delimiter = '\t'
        else:
            delimiter = None
        
        # 4. Ищем нужные SNP
        genetics_result = {}
        
        # Словарь соответствия rsid -> наш ген
        target_snp = {
            'rs1801133': 'MTHFR',   # MTHFR
            'rs9939609': 'FTO',      # FTO
            'rs1815739': 'ACTN3'     # ACTN3
        }
        
        # Проходим по строкам
        found_count = 0
        for line in lines:
            if line.startswith('#') or not line.strip():
                continue  # пропускаем комментарии и пустые строки
            
            if delimiter:
                parts = line.split(delimiter)
                if len(parts) >= 4:
                    rsid = parts[0].strip()
                    if rsid in target_snp:
                        genotype = parts[3].strip().replace('/', '')
                        genetics_result[target_snp[rsid]] = genotype
                        found_count += 1
        
        # 5. Проверяем, что нашли все три
        if found_count < 3:
            await message.answer(
                f"❌ Найдено только {found_count} из 3 маркеров.\n"
                f"Попробуй другой файл или введи данные вручную через /genetics"
            )
            await state.clear()
            return
        
        # 6. Сохраняем в базу
        update_user_db(message.from_user.id, {
            'genetics_mthfr': genetics_result.get('MTHFR', ''),
            'genetics_fto': genetics_result.get('FTO', ''),
            'genetics_actn3': genetics_result.get('ACTN3', ''),
            'genetics_consent': 1
        })
        
        # 7. Генерируем отчет
        result = generate_genetics_report(
            genetics_result.get('MTHFR', ''),
            genetics_result.get('FTO', ''),
            genetics_result.get('ACTN3', '')
        )
        
        await message.answer(result)
        await state.clear()
        
        # Показываем меню
        user = get_user(message.from_user.id)
        if user:
            kb = ReplyKeyboardBuilder()
            for btn in [BotTexts.BTN_WAKE, BotTexts.BTN_PERIODS, BotTexts.BTN_SOS, 
                        BotTexts.BTN_WORK, BotTexts.BTN_CHEAT, BotTexts.BTN_PROFILE, 
                        BotTexts.BTN_STATS, BotTexts.BTN_GENETICS, BotTexts.BTN_AI]:
                kb.button(text=btn)
            await message.answer("Главное меню:", reply_markup=kb.adjust(2).as_markup(resize_keyboard=True))
        
    except Exception as e:
        await message.answer(f"❌ Ошибка при обработке файла: {e}")
        await state.clear()

@dp.message(Reg.genetics_file_upload)
async def invalid_file_upload(message: types.Message, state: FSMContext):
    await message.answer(
        "❌ Пожалуйста, отправь **файл** с генетическими данными.\n"
        "Если хочешь ввести вручную, начни заново: /genetics"
    )


@dp.message(Reg.genetics_mthfr)
async def process_genetics_mthfr(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    # Просто проверяем, что выбран допустимый вариант
    valid_options = ["✅ Норма (C/C)", "⚠️ Гетерозигота (C/T)", "🔴 Гомозигота (T/T)"]
    if message.text not in valid_options:
        return await message.answer(
            "❓ Пожалуйста, выбери вариант из кнопок выше."
        )
    
    await state.update_data(genetics_mthfr=message.text)
    
    # FTO вопрос
    kb = ReplyKeyboardBuilder()
    kb.button(text="✅ TT — нормальный риск")
    kb.button(text="⚠️ AT — повышенный риск")
    kb.button(text="🔴 AA — высокий риск")
    kb.adjust(1)
    
    await message.answer(
        "🧬 **Ген FTO** (риск ожирения)\n\n"
        "Выбери свой вариант:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    await state.set_state(Reg.genetics_fto)

@dp.message(Reg.genetics_fto)
async def process_genetics_fto(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    valid_options = ["✅ TT — нормальный риск", "⚠️ AT — повышенный риск", "🔴 AA — высокий риск"]
    if message.text not in valid_options:
        return await message.answer(
            "❓ Пожалуйста, выбери вариант из кнопок выше."
        )
    
    await state.update_data(genetics_fto=message.text)
    
    # ACTN3 вопрос
    kb = ReplyKeyboardBuilder()
    kb.button(text="💪 Взрывной тип (RR/RX)")
    kb.button(text="🏃 Выносливый тип (XX)")
    kb.adjust(1)
    
    await message.answer(
        "🧬 **Ген ACTN3** (тип мышечных волокон)\n\n"
        "Выбери свой вариант:",
        reply_markup=kb.as_markup(resize_keyboard=True)
    )
    await state.set_state(Reg.genetics_actn3)
    
    
@dp.message(Reg.genetics_actn3)
async def process_genetics_actn3(message: types.Message, state: FSMContext):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    valid_options = ["💪 Взрывной тип (RR/RX)", "🏃 Выносливый тип (XX)"]
    if message.text not in valid_options:
        return await message.answer(
            "❓ Пожалуйста, выбери вариант из кнопок выше."
        )
    
    await state.update_data(genetics_actn3=message.text)
    
    data = await state.get_data()
    
    update_user_db(message.from_user.id, {
        'genetics_mthfr': data.get('genetics_mthfr', ''),
        'genetics_fto': data.get('genetics_fto', ''),
        'genetics_actn3': data.get('genetics_actn3', ''),
        'genetics_consent': 1
    })
    
    result = generate_genetics_report(
        data.get('genetics_mthfr', ''),
        data.get('genetics_fto', ''),
        data.get('genetics_actn3', '')
    )
    
    await message.answer(result, reply_markup=types.ReplyKeyboardRemove())
    await state.clear()
    
    user = get_user(message.from_user.id)
    if user:
        kb = ReplyKeyboardBuilder()
        for btn in [BotTexts.BTN_WAKE, BotTexts.BTN_PERIODS, BotTexts.BTN_SOS, 
                    BotTexts.BTN_WORK, BotTexts.BTN_CHEAT, BotTexts.BTN_PROFILE, 
                    BotTexts.BTN_STATS, BotTexts.BTN_AI, "🧬 Генетика"]:
            kb.button(text=btn)
        await message.answer("Главное меню:", reply_markup=kb.adjust(2).as_markup(resize_keyboard=True))

# ==================== АДМИНСКИЕ КОМАНДЫ ====================
@dp.message(Command("admin"))
async def admin_panel(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM users")
        total_users = cur.fetchone()[0]
        cur.execute("SELECT SUM(bio_points) FROM users")
        total_points = cur.fetchone()[0] or 0
    
    await message.answer(f"🔐 **Админ панель**\n\n"
                        f"👥 Всего пользователей: {total_users}\n"
                        f"⭐ Всего очков: {total_points}")

@dp.message(Command("reset"))
async def reset_command(message: types.Message, state: FSMContext):
    await state.clear()
    
    with sqlite3.connect(DB_NAME) as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id = ?", (message.from_user.id,))
        cur.execute("DELETE FROM morning_checkin WHERE user_id = ?", (message.from_user.id,))
        cur.execute("DELETE FROM evening_audit WHERE user_id = ?", (message.from_user.id,))
        conn.commit()
    
    await message.answer("🔄 Все данные сброшены. Отправь /start для новой регистрации.")

@dp.message(Command("debug_day"))
async def debug_day(message: types.Message):
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Нет пользователя")
    
    today = date.today()
    rhythm_start = date.fromisoformat(user['rhythm_start'])
    days_diff = (today - rhythm_start).days
    cns_day = days_diff % 9 + 1
    
    debug = f"🔍 **Отладка:**\n"
    debug += f"📅 Сегодня: {today}\n"
    debug += f"🎯 Старт ритма: {rhythm_start}\n"
    debug += f"📊 Прошло дней: {days_diff}\n"
    debug += f"🔢 День ЦНС: {cns_day}\n"
    
    if user['gender_type'] == 1:
        cycle_start = date.fromisoformat(user['cycle_start'])
        cycle_day = (today - cycle_start).days % user['cycle_length'] + 1
        debug += f"🩸 День цикла: {cycle_day}\n"
    
    await message.answer(debug)

# ==================== ВОДНЫЙ МОДУЛЬ ====================
@dp.message(F.text == "💧 ВОДА")
async def water_handler(message: types.Message):
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    print("✅ Обработчик воды сработал!")
    
    from water_calculator import WaterCalculator
    import json
    from utils import get_user, update_user_db
    
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("Сначала пройди регистрацию: /start")
        return
    
    # Получаем или рассчитываем норму
    if not user.get('water_goal'):
        # Расчет нормы
        total = WaterCalculator.calculate_total(user)
        
        # Получаем расписание
        wake_hour = int(user['wake_time'].split(':')[0]) if user.get('wake_time') else 7
        schedule = WaterCalculator.get_schedule(total, wake_hour)
        
        water_plan = {'total': total, 'schedule': schedule}
        
        # Адаптация под цикл и цель
        # (если нужны дополнительные адаптации)
        
        update_user_db(message.from_user.id, {
            'water_goal': total,
            'water_preferences': json.dumps(water_plan, ensure_ascii=False)
        })
    else:
        total = user['water_goal']
        water_plan = json.loads(user.get('water_preferences', '{}'))
        if not water_plan:
            wake_hour = int(user['wake_time'].split(':')[0]) if user.get('wake_time') else 7
            water_plan = {'total': total, 'schedule': WaterCalculator.get_schedule(total, wake_hour)}
    
    # Формируем отчет
    user_data = {**user, 'water_goal': total, 'water_consumed_today': user.get('water_consumed_today', 0)}
    report = WaterCalculator.format_report(user_data)
    
    # Кнопки
    kb = InlineKeyboardBuilder()
    kb.button(text="💧 Отметить стакан", callback_data="water_log")
    kb.button(text="📅 Расписание", callback_data="water_schedule")
    kb.button(text="🧹 Домохозяйка", callback_data="water_motilin")
    kb.button(text="🧠 Как считается?", callback_data="water_explain")
    kb.adjust(2)
    
    await message.answer(report, reply_markup=kb.as_markup())

# ==================== ОБРАБОТЧИКИ КНОПОК ВОДЫ ====================

@dp.callback_query(F.data == "water_log")
async def water_log_callback(callback: types.CallbackQuery):
    """Отметить выпитый стакан"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди регистрацию", show_alert=True)
        return
    
    # Получаем текущий прогресс
    consumed = user.get('water_consumed_today', 0)
    goal = user.get('water_goal', 2000)
    
    # Добавляем стакан (примерно 250 мл)
    new_consumed = consumed + 250
    if new_consumed > goal:
        new_consumed = goal
    
    # Сохраняем
    update_user_db(callback.from_user.id, {'water_consumed_today': new_consumed})
    
    # Начисляем очки
    await award_points(callback.from_user.id, "water_glass", callback.message)
    
    await callback.answer(f"✅ +250 мл! Прогресс: {new_consumed}/{goal} мл")
    
    # Обновляем сообщение с водным балансом
    # Можно перезапустить water_handler или просто показать новое сообщение

@dp.callback_query(F.data == "water_schedule")
async def water_schedule_callback(callback: types.CallbackQuery):
    """Показать полное расписание"""
    from water_calculator import WaterCalculator
    import json
    
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди регистрацию", show_alert=True)
        return
    
    total = user.get('water_goal', 2000)
    water_plan = json.loads(user.get('water_preferences', '{}'))
    
    if not water_plan or 'schedule' not in water_plan:
        wake_hour = int(user['wake_time'].split(':')[0]) if user.get('wake_time') else 7
        schedule = WaterCalculator.get_schedule(total, wake_hour)
    else:
        schedule = water_plan.get('schedule', [])
    
    text = "⏰ **Полное расписание воды:**\n\n"
    for item in schedule:
        text += f"**{item['time']}** – {item['name']}\n"
        text += f"📏 {item['ml']} мл, {item['type']}\n"
        text += f"🧹 {item.get('motilin', '')}\n\n"
    
    await callback.message.answer(text)
    await callback.answer()

@dp.callback_query(F.data == "water_motilin")
async def water_motilin_callback(callback: types.CallbackQuery):
    """Информация о пищевой домохозяйке"""
    text = """
🧹 **Пищевая домохозяйка (мотилин)**

**Что это?**
Мотилин — гормон, который запускает «волны чистки» в кишечнике между приемами пищи.

**Как работает?**
Каждые 90-100 минут мотилин создает мощные сокращения, которые:
• Сметают остатки пищи
• Удаляют бактерии
• Готовят кишечник к следующему приему

**Связь с водой:**
Вода стимулирует выработку мотилина. Каждый стакан воды = сигнал домохозяйке начать уборку.

**Результат:**
✅ Нет вздутия
✅ Меньше ложного голода
✅ Лучшее усвоение пищи
"""
    await callback.message.answer(text)
    await callback.answer()

# ==================== ОБРАБОТЧИКИ КНОПОК ВОДЫ ====================

@dp.callback_query(F.data == "water_log")
async def water_log_callback(callback: types.CallbackQuery):
    """Отметить выпитый стакан"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди регистрацию", show_alert=True)
        return
    
    # Получаем текущий прогресс
    consumed = user.get('water_consumed_today', 0)
    goal = user.get('water_goal', 2000)
    
    # Добавляем стакан (примерно 250 мл)
    new_consumed = consumed + 250
    if new_consumed > goal:
        new_consumed = goal
    
    # Сохраняем
    update_user_db(callback.from_user.id, {'water_consumed_today': new_consumed})
    
    # Начисляем очки
    await award_points(callback.from_user.id, "water_glass", callback.message)
    
    await callback.answer(f"✅ +250 мл! Прогресс: {new_consumed}/{goal} мл")
    
    # Обновляем сообщение с водным балансом
    # Можно перезапустить water_handler или просто показать новое сообщение

@dp.callback_query(F.data == "water_schedule")
async def water_schedule_callback(callback: types.CallbackQuery):
    """Показать полное расписание"""
    from water_calculator import WaterCalculator
    import json
    
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди регистрацию", show_alert=True)
        return
    
    total = user.get('water_goal', 2000)
    water_plan = json.loads(user.get('water_preferences', '{}'))
    
    # 👇 ИСПРАВЛЕНО: получаем время пробуждения
    wake_hour = int(user['wake_time'].split(':')[0]) if user.get('wake_time') else 7
    
    if not water_plan or 'schedule' not in water_plan:
        # 👇 ИСПРАВЛЕНО: вызываем правильный метод
        schedule = WaterCalculator.get_schedule(total, wake_hour)
    else:
        schedule = water_plan.get('schedule', [])
    
    text = "⏰ **Полное расписание воды:**\n\n"
    for item in schedule:
        text += f"**{item['time']}** – {item['name']}\n"
        text += f"📏 {item['ml']} мл, {item['type']}\n"
        text += f"🧹 {item.get('motilin', '')}\n\n"
    
    await callback.message.answer(text)
    await callback.answer()
@dp.callback_query(F.data == "water_motilin")
async def water_motilin_callback(callback: types.CallbackQuery):
    """Информация о пищевой домохозяйке"""
    text = """
🧹 **Пищевая домохозяйка (мотилин)**

**Что это?**
Мотилин — гормон, который запускает «волны чистки» в кишечнике между приемами пищи.

**Как работает?**
Каждые 90-100 минут мотилин создает мощные сокращения, которые:
• Сметают остатки пищи
• Удаляют бактерии
• Готовят кишечник к следующему приему

**Связь с водой:**
Вода стимулирует выработку мотилина. Каждый стакан воды = сигнал домохозяйке начать уборку.

**Результат:**
✅ Нет вздутия
✅ Меньше ложного голода
✅ Лучшее усвоение пищи
"""
    await callback.message.answer(text)
    await callback.answer()


# ==================== НОВЫЕ КОМАНДЫ ====================

@dp.message(Command("protocol"))
async def show_protocol_table(message: types.Message):
    """Показать полную таблицу нагрузок"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    text = """
📋 **ПОЛНАЯ ТАБЛИЦА НАГРУЗОК**
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

🔥 **ПО ДНЯМ ЖЕНСКОГО ЦИКЛА:**

🌸 **Дни 1-5: МЕНСТРУАЦИЯ** (энергия 20%)
├ ❌ HIIT ЗАПРЕЩЕН
├ 🧘 Только йога и растяжка
├ 🍽 Железо + вит. C, без кофеина
└ 💧 Теплая вода

🌱 **Дни 6-12: ФОЛЛИКУЛЯРНАЯ** (энергия 80%)
├ ✅ HIIT разрешен
├ 🧠 Интеллектуальные задачи
├ 🍽 Белок (яйца, рыба, мясо)
└ 💧 Обычный режим

⚡ **Дни 13-16: ОВУЛЯЦИЯ** (энергия 100%)
├ 🚀 ДВОЙНОЙ HIIT! ПИК ФОРМЫ!
├ 🏋️‍♀️ Тяжелые тренировки, рекорды
├ 🍽 Сложные углеводы (гречка)
└ 💧 Усиленный режим

🌿 **Дни 17-24: ЛЮТЕИНОВАЯ** (энергия 60%)
├ ✅ Легкий HIIT
├ 📊 Планирование, внимательность
├ 🍽 Магний (зелень, орехи)
└ 💧 Обычный режим

🍂 **Дни 25-28: ПМС/ДЕТОКС** (энергия 30%)
├ ❌ HIIT ЗАПРЕЩЕН
├ 🚶 Только прогулки, лимфодренаж
├ 🍽 Калий (авокадо, курага), минимум соли
└ 💧 Щелочная вода

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

🧠 **ПО ДНЯМ ЦНС (9-ДНЕВНЫЙ ЦИКЛ):**

📅 **День 1: ЗАПУСК** (70%) — вход в ритм
📅 **День 2: ПИК А** (100%) — МАКСИМУМ
📅 **День 3: ПЛАТО** (90%) — стабильно
📅 **День 4: БУФЕР** (50%) — облегченный
📅 **День 5: ПИК Б** (100%) — вторая волна
📅 **День 6: СТАБИЛЬНОСТЬ** (80%) — закрепление
📅 **День 7: ДЕТОКС** (30%) — очищение
📅 **День 8: ДУША** (20%) — хобби, отдых
📅 **День 9: ТИШИНА** (10%) — ПОЛНЫЙ ОТДЫХ

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

⚡ **КОМБИНИРОВАННЫЕ ПРОТОКОЛЫ:**

🔴 **КРИТИЧЕСКИЙ ДЕНЬ** (<20%)
├ ПМС (25-28) + ТИШИНА (день 9)
└ Только отдых, ранний сон

🟡 **НИЗКАЯ ЭНЕРГИЯ** (20-50%)
├ Менструация/ПМС + ДЕТОКС/ДУША
└ Йога, растяжка, прогулки

🟢 **СРЕДНЯЯ ЭНЕРГИЯ** (50-80%)
├ Лютеиновая + СТАБИЛЬНОСТЬ
└ Умеренные тренировки

💪 **ВЫСОКАЯ ЭНЕРГИЯ** (80-100%)
├ Фолликулярная + ПИК/ПЛАТО
└ HIIT, силовые, сложные задачи

🚀 **МАКСИМАЛЬНАЯ** (130-200%)
├ Овуляция + ПИК (дни 2 или 5)
└ ДВОЙНОЙ HIIT, рекорды!

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

Твой сегодняшний день: /day
"""
    
    await message.answer(text)


@dp.message(Command("day"))
async def show_today_protocol(message: types.Message):
    """Показать протокол на сегодня"""
    from rhythm_core import get_combined_recommendation, get_cns_phase, get_female_phase
    from datetime import date
    
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    today = date.today()
    
    # День ЦНС
    rhythm_start = date.fromisoformat(user['rhythm_start'])
    cns_day = (today - rhythm_start).days % 9 + 1
    cns = get_cns_phase(cns_day)
    
    text = f"📅 **ТВОЙ ДЕНЬ {today.strftime('%d.%m.%Y')}**\n\n"
    text += f"🧠 **ЦНС:** День {cns_day} — {cns['name']} ({cns['energy']*100:.0f}%)\n"
    
    if user['gender_type'] == 1:
        cycle_start = date.fromisoformat(user['cycle_start'])
        cycle_length = user.get('cycle_length', 28)
        female_day = (today - cycle_start).days % cycle_length + 1
        female = get_female_phase(female_day, cycle_length)
        
        text += f"🩸 **Цикл:** День {female_day} — {female['name']} ({female['energy']*100:.0f}%)\n\n"
        
        rec = get_combined_recommendation(female_day, cns_day, cycle_length)
        text += f"⚡ **ИТОГОВАЯ ЭНЕРГИЯ:** {rec['energy']}%\n"
        text += f"💪 **РЕКОМЕНДАЦИЯ:** {rec['load']}\n"
        text += f"🥗 **ПИТАНИЕ:** {rec['nutrition']}"
    else:
        text += f"\n⚡ **ЭНЕРГИЯ:** {cns['energy']*100:.0f}%\n"
        text += f"💪 **НАГРУЗКА:** {cns['load']}"
    
    await message.answer(text)

@dp.message(Command("risk"))
async def show_risk_analysis(message: types.Message):
    """Показать интегральный риск-анализ"""
    from cycle_integration import CycleIntegrator
    
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    integrator = CycleIntegrator(user)
    report = integrator.get_daily_risk_report()
    
    await message.answer(report)

@dp.message(Command("water"))
async def cmd_water(message: types.Message):
    """Показать водный баланс"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    from water_calculator import WaterCalculator
    import json
    
    # Теперь используем тот же код, что и в кнопке
    if not user.get('water_goal'):
        total = WaterCalculator.calculate_total(user)
        wake_hour = int(user['wake_time'].split(':')[0]) if user.get('wake_time') else 7
        schedule = WaterCalculator.get_schedule(total, wake_hour)
        water_plan = {'total': total, 'schedule': schedule}
        
        update_user_db(message.from_user.id, {
            'water_goal': total,
            'water_preferences': json.dumps(water_plan, ensure_ascii=False)
        })
    else:
        total = user['water_goal']
    
    user_data = {**user, 'water_goal': total, 'water_consumed_today': user.get('water_consumed_today', 0)}
    report = WaterCalculator.format_report(user_data)
    
    kb = InlineKeyboardBuilder()
    kb.button(text="💧 Отметить стакан", callback_data="water_log")
    kb.button(text="📅 Расписание", callback_data="water_schedule")
    kb.button(text="🧹 Домохозяйка", callback_data="water_motilin")
    kb.button(text="🧠 Как считается?", callback_data="water_explain")
    kb.adjust(2)
    
    await message.answer(report, reply_markup=kb.as_markup())


@dp.message(Command("moon"))
async def show_moon(message: types.Message):
    """Показать лунный календарь"""
    from lunar import LunarScience, format_lunar_report
    
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    lunar = LunarScience()
    data = lunar.get_full_recommendation()
    report = format_lunar_report(data)
    
    await message.answer(report)

# ==================== ОБРАБОТЧИКИ СТАТИСТИКИ ====================
@dp.callback_query(F.data.startswith("stat_") | F.data.startswith("export_"))
async def statistics_callback_handler(callback: types.CallbackQuery):
    """Обработчик всех callback'ов статистики"""
    from statistics import handle_stat_callback
    await handle_stat_callback(callback)



# ==================== ЗАПУСК ====================
async def main():
    """Главная функция запуска"""
    print("\n" + "="*50)
    print("🚀 ЗАПУСК БОТА 'КОД РЕВЕРС'")
    print("="*50)
    
    print("\n🔄 Инициализация базы данных...")
    if init_db():
        print("✅ База данных готова")
    else:
        print("❌ Ошибка базы данных!")
        return
    
    print("\n🔄 Инициализация системы геймификации...")
    # 👇 ВОТ ЭТО МЕСТО! ГЛОБАЛЬНАЯ ПЕРЕМЕННАЯ
    global gamification
    gamification = GamificationSystem(sqlite3.connect(DB_NAME))
    print("✅ Система геймификации запущена")
    
    # Регистрируем роутеры ТОЛЬКО ОДИН РАЗ!
    print("\n🔄 Регистрация роутеров...")
    
    # Импортируем роутеры здесь, чтобы избежать циклических импортов
    from menu import menu_router
    from mindful_eating import mindful_router
    from water_calculator import water_router  # 👈 ДОБАВЛЯЕМ ЭТОТ ИМПОРТ
    
    dp.include_router(menu_router)
    dp.include_router(mindful_router)
    dp.include_router(water_router)  # 👈 ДОБАВЛЯЕМ РЕГИСТРАЦИЮ
    
    print("✅ Все роутеры зарегистрированы")
    
    # ===== GigaChat RAG =====
    import os
    from dotenv import load_dotenv
    from gigachat_rag import GigaChatRAG
    
    load_dotenv()
    
    global rag
    GIGACHAT_AUTH_KEY = os.getenv('GIGACHAT_AUTH_KEY')
    if not GIGACHAT_AUTH_KEY:
        print("⚠️ GIGACHAT_AUTH_KEY не найден в .env")
        rag = None
    else:
        rag = GigaChatRAG(GIGACHAT_AUTH_KEY)
        print("✅ GigaChat RAG инициализирован")
    
    print("\n🔄 Запуск планировщика...")
    scheduler.start()
    await setup_all_schedules()
    print("✅ Планировщик запущен")
    
    print("\n🔄 Запуск бота...")
    await bot.delete_webhook(drop_pending_updates=True)
    bot_info = await bot.get_me()
    print(f"✅ Бот @{bot_info.username} запущен!")
    print("\n" + "="*50)
    print("📱 Иди в Telegram и напиши /start")
    print("="*50 + "\n")
    
    await dp.start_polling(bot, skip_updates=True)


# ВАШ ЗАПУСК 
if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n❌ Бот остановлен пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
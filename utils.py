# utils.py
print("🔥 UTILS.PY ЗАГРУЖАЕТСЯ 🔥")

import sqlite3
from datetime import datetime, date, timedelta
from collections import defaultdict
import time
import json
import re

DB_NAME = 'users.db'

print("✅ Импорты в utils.py выполнены")

# ==================== РАБОТА С БАЗОЙ ДАННЫХ ====================
def get_user(user_id: int):
    """Получить данные пользователя по ID"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cur.fetchone()
            if user:
                print(f"✅ Пользователь {user_id} найден в БД")
                return dict(user)
            else:
                print(f"❌ Пользователь {user_id} НЕ найден в БД")
                return None
    except Exception as e:
        print(f"❌ Ошибка получения пользователя {user_id}: {e}")
        return None

def update_user_db(user_id: int, data: dict):
    """Обновить данные пользователя"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            for key, value in data.items():
                cur.execute(f"UPDATE users SET {key} = ? WHERE user_id = ?", (value, user_id))
            conn.commit()
        return True
    except Exception as e:
        print(f"❌ Error updating user {user_id}: {e}")
        return False

def get_all_users():
    """Получить всех пользователей"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users")
            users = cur.fetchall()
        return [dict(user) for user in users]
    except Exception as e:
        print(f"❌ Error getting all users: {e}")
        return []

def user_exists(user_id: int) -> bool:
    """Проверить, существует ли пользователь"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            cur.execute("SELECT 1 FROM users WHERE user_id = ?", (user_id,))
            return cur.fetchone() is not None
    except Exception as e:
        print(f"❌ Error checking user {user_id}: {e}")
        return False

def add_user_complete(user_id: int, user_data: dict):
    """Полное добавление пользователя (все поля)"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            
            # Подготавливаем поля
            fields = ['user_id'] + list(user_data.keys())
            values = [user_id] + list(user_data.values())
            placeholders = ','.join(['?'] * len(values))
            
            query = f"INSERT OR REPLACE INTO users ({','.join(fields)}) VALUES ({placeholders})"
            cur.execute(query, values)
            conn.commit()
            return True
    except Exception as e:
        print(f"❌ Error adding user {user_id}: {e}")
        return False

# ==================== ПРОВЕРКА ДОСТУПА ====================
def has_access(user_id, required_level):
    """
    Проверяет уровень доступа пользователя
    required_level: 'free', 'core', 'vip'
    """
    user = get_user(user_id)
    if not user:
        return False
    
    status = user.get('subscription_status', 'free')
    until = user.get('subscription_until')
    
    # Проверяем, не истекла ли подписка
    if until and status != 'free':
        try:
            until_date = date.fromisoformat(until)
            if until_date < date.today():
                # Подписка истекла
                update_user_db(user_id, {'subscription_status': 'free'})
                return False
        except:
            pass
    
    if required_level == 'free':
        return True
    elif required_level == 'core':
        return status in ['core', 'vip']
    elif required_level == 'vip':
        return status == 'vip'
    
    return False

def get_subscription_info(user_id):
    """Получить информацию о подписке"""
    user = get_user(user_id)
    if not user:
        return None
    
    status = user.get('subscription_status', 'free')
    until = user.get('subscription_until')
    
    status_names = {
        'free': '🆓 Бесплатный',
        'core': '⭐ CORE',
        'vip': '💎 VIP'
    }
    
    result = {
        'status': status,
        'status_name': status_names.get(status, '🆓 Бесплатный'),
        'until': until,
        'is_active': True
    }
    
    if until and status != 'free':
        try:
            until_date = date.fromisoformat(until)
            result['is_active'] = until_date >= date.today()
            result['days_left'] = (until_date - date.today()).days if result['is_active'] else 0
        except:
            result['days_left'] = 0
    
    return result

# ==================== ЗАЩИТА ОТ СПАМА ====================
user_last_message = defaultdict(float)
user_message_count = defaultdict(list)

async def check_rate_limit(user_id):
    """Проверяет, не спамит ли пользователь"""
    now = time.time()
    
    # Проверка на сообщения чаще чем раз в секунду
    last = user_last_message.get(user_id, 0)
    if now - last < 1:
        return False, "⏳ Слишком быстро! Подожди секунду."
    
    # Проверка на больше 10 сообщений в минуту
    user_message_count[user_id] = [t for t in user_message_count[user_id] if now - t < 60]
    if len(user_message_count[user_id]) >= 10:
        return False, "⏳ Слишком много сообщений. Отдохни минутку."
    
    user_last_message[user_id] = now
    user_message_count[user_id].append(now)
    return True, ""

def reset_rate_limit(user_id):
    """Сбросить лимиты для пользователя"""
    if user_id in user_last_message:
        del user_last_message[user_id]
    if user_id in user_message_count:
        del user_message_count[user_id]

# ==================== ЗАЩИТА ОТ РЕГИСТРАЦИОННОГО СПАМА ====================
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

# ==================== ВАЛИДАЦИЯ ДАННЫХ ====================
def validate_time(time_str: str) -> bool:
    """Проверка формата времени ЧЧ:ММ"""
    pattern = r'^([0-1]?[0-9]|2[0-3]):[0-5][0-9]$'
    return bool(re.match(pattern, time_str))

def validate_date(date_str: str) -> bool:
    """Проверка формата даты ДД.ММ.ГГГГ"""
    try:
        datetime.strptime(date_str, "%d.%m.%Y")
        return True
    except:
        return False

def validate_number(value: str, min_val=None, max_val=None) -> bool:
    """Проверка, что строка является числом в диапазоне"""
    try:
        num = float(value)
        if min_val is not None and num < min_val:
            return False
        if max_val is not None and num > max_val:
            return False
        return True
    except ValueError:
        return False

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

# ==================== РАБОТА С ДОСТИЖЕНИЯМИ ====================
def add_achievement(user_id: int, achievement_key: str):
    """Добавить достижение пользователю"""
    user = get_user(user_id)
    if not user:
        return False
    
    try:
        achievements = json.loads(user.get('achievements', '[]'))
    except:
        achievements = []
    
    if achievement_key not in achievements:
        achievements.append(achievement_key)
        update_user_db(user_id, {'achievements': json.dumps(achievements)})
        return True
    
    return False

def get_achievements(user_id: int):
    """Получить достижения пользователя"""
    user = get_user(user_id)
    if not user:
        return []
    
    try:
        return json.loads(user.get('achievements', '[]'))
    except:
        return []

# ==================== РАБОТА СО СТАТИСТИКОЙ ====================
def get_user_stats(user_id: int):
    """Получить общую статистику пользователя"""
    stats = {
        'morning_checkins': 0,
        'evening_audits': 0,
        'weekly_metrics': 0,
        'last_morning': None,
        'last_evening': None,
        'streak': 0
    }
    
    try:
        with sqlite3.connect(DB_NAME) as conn:
            cur = conn.cursor()
            
            # Утренние замеры
            cur.execute("SELECT COUNT(*), MAX(date) FROM morning_checkin WHERE user_id = ?", (user_id,))
            count, last = cur.fetchone()
            stats['morning_checkins'] = count or 0
            stats['last_morning'] = last
            
            # Вечерние аудиты
            cur.execute("SELECT COUNT(*), MAX(date) FROM evening_audit WHERE user_id = ?", (user_id,))
            count, last = cur.fetchone()
            stats['evening_audits'] = count or 0
            stats['last_evening'] = last
            
            # Недельные замеры
            cur.execute("SELECT COUNT(*) FROM weekly_metrics WHERE user_id = ?", (user_id,))
            stats['weekly_metrics'] = cur.fetchone()[0] or 0
            
            # Подсчет streak (последовательных дней активности)
            cur.execute("""
                SELECT DISTINCT date FROM (
                    SELECT date FROM morning_checkin WHERE user_id = ?
                    UNION
                    SELECT date FROM evening_audit WHERE user_id = ?
                ) ORDER BY date DESC
            """, (user_id, user_id))
            
            dates = [row[0] for row in cur.fetchall()]
            if dates:
                streak = 1
                current_date = date.fromisoformat(dates[0])
                
                for i in range(1, len(dates)):
                    prev_date = date.fromisoformat(dates[i-1])
                    curr_date = date.fromisoformat(dates[i])
                    if (prev_date - curr_date).days == 1:
                        streak += 1
                    else:
                        break
                
                stats['streak'] = streak
    
    except Exception as e:
        print(f"❌ Error getting stats for {user_id}: {e}")
    
    return stats

# ==================== РАБОТА С КОНФИГАМИ ====================
def get_bot_config():
    """Получить конфигурацию бота"""
    return {
        'db_name': DB_NAME,
        'version': '1.0.0',
        'name': 'Код Реверс'
    }

print("✅ Все функции в utils.py определены")
print("🔥🔥🔥 UTILS.PY ЗАГРУЗКА ЗАВЕРШЕНА 🔥🔥🔥")

# ==================== ЭКСПОРТ ====================
__all__ = [
    'get_user', 'update_user_db', 'get_all_users', 'user_exists', 'add_user_complete',
    'has_access', 'get_subscription_info',
    'check_rate_limit', 'reset_rate_limit', 'check_registration_spam',
    'validate_time', 'validate_date', 'validate_number', 'sanitize_input',
    'add_achievement', 'get_achievements',
    'get_user_stats', 'get_bot_config'
]
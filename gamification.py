# gamification.py
print("🔥 GAMIFICATION.PY ЗАГРУЖАЕТСЯ 🔥")

import json
import sqlite3
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple

DB_NAME = 'users.db'

print("✅ Импорты в gamification.py выполнены")

# Звания для женщин
FEMALE_TITLES = [
    {"id": "novice", "min": 0, "max": 49, "name": "Пробуждение", "emoji": "👶", 
     "desc": "Ты только начинаешь путь к себе"},
    {"id": "sprout", "min": 50, "max": 149, "name": "Росток", "emoji": "🌱", 
     "desc": "Первые всходы новой жизни"},
    {"id": "bloom", "min": 150, "max": 299, "name": "Цветущая", "emoji": "🌸", 
     "desc": "Раскрываешь свой потенциал"},
    {"id": "lunar", "min": 300, "max": 499, "name": "Лунная Странница", "emoji": "🌙", 
     "desc": "Идёшь в ритме природы"},
    {"id": "star", "min": 500, "max": 749, "name": "Звездная Дева", "emoji": "⭐", 
     "desc": "Сияешь ярче звёзд"},
    {"id": "fury", "min": 750, "max": 999, "name": "Огненная Фурия", "emoji": "🔥", 
     "desc": "Неудержимая сила"},
    {"id": "goddess", "min": 1000, "max": 999999, "name": "Богиня Времени", "emoji": "👑", 
     "desc": "Повелительница ритмов"}
]

# Звания для мужчин
MALE_TITLES = [
    {"id": "seeker", "min": 0, "max": 49, "name": "Искатель", "emoji": "👶", 
     "desc": "В поисках истины"},
    {"id": "wanderer", "min": 50, "max": 149, "name": "Странник", "emoji": "⚔️", 
     "desc": "Путь только начинается"},
    {"id": "defender", "min": 150, "max": 299, "name": "Защитник", "emoji": "🛡️", 
     "desc": "Стоишь на страже ритма"},
    {"id": "wolf", "min": 300, "max": 499, "name": "Морской Волк", "emoji": "🌊", 
     "desc": "Покоряешь стихии"},
    {"id": "thunder", "min": 500, "max": 749, "name": "Громовержец", "emoji": "⚡", 
     "desc": "Власть над энергией"},
    {"id": "dragon", "min": 750, "max": 999, "name": "Дракон", "emoji": "🔥", 
     "desc": "Дышишь огнём"},
    {"id": "guardian", "min": 1000, "max": 999999, "name": "Хранитель Времени", "emoji": "👑", 
     "desc": "Властелин циклов"}
]

# Достижения
ACHIEVEMENTS = {
    "first_blood": {
        "name": "Первый шаг",
        "desc": "Пройди первую регистрацию",
        "emoji": "👣",
        "points": 10,
        "hidden": False
    },
    "morning_routine": {
        "name": "Ранняя пташка",
        "desc": "Сделал(а) утренний опрос",
        "emoji": "🐦",
        "points": 10,
        "hidden": False
    },
    "log_filled": {
        "name": "Дневник",
        "desc": "Заполнил(а) вечерний дневник",
        "emoji": "📓",
        "points": 5,
        "hidden": False
    },
    "cycle_honest": {
        "name": "Честный цикл",
        "desc": "Отметила начало цикла",
        "emoji": "🩸",
        "points": 15,
        "hidden": False
    },
    "sos_used": {
        "name": "Самопомощь",
        "desc": "Справился(ась) со срывом сам(а)",
        "emoji": "🆘",
        "points": 5,
        "hidden": False
    },
    "sos_pro_used": {
        "name": "Профессиональная помощь",
        "desc": "Обратился(ась) к психологу",
        "emoji": "👩‍⚕️",
        "points": -50,
        "hidden": False
    },
    "meditation": {
        "name": "Медитация",
        "desc": "Практиковал(а) осознанность",
        "emoji": "🧘",
        "points": 10,
        "hidden": False
    },
    "hiit_done": {
        "name": "HIIT-герой",
        "desc": "Выполнил(а) HIIT-тренировку",
        "emoji": "⚡",
        "points": 20,
        "hidden": False
    },
    "water_glass": {
        "name": "Водный баланс",
        "desc": "Выпил(а) стакан воды",
        "emoji": "💧",
        "points": 1,
        "hidden": False
    },
    "streak_7": {
        "name": "Неделя без пропусков",
        "desc": "7 дней подряд заполнял(а) дневник",
        "emoji": "🔥",
        "points": 50,
        "hidden": False
    },
    "streak_30": {
        "name": "Месяц осознанности",
        "desc": "30 дней подряд без пропусков",
        "emoji": "⭐",
        "points": 200,
        "hidden": False
    },
    "century": {
        "name": "Центурион",
        "desc": "Набрал 100 очков",
        "emoji": "💯",
        "points": 20,
        "hidden": False
    },
    "half_k": {
        "name": "Полутысячник",
        "desc": "Набрал 500 очков",
        "emoji": "🎯",
        "points": 50,
        "hidden": False
    },
    "grand": {
        "name": "Гранд-мастер",
        "desc": "Набрал 1000 очков",
        "emoji": "🏆",
        "points": 100,
        "hidden": False
    }
}

# Действия и очки
ACTIONS = {
    "first_blood": {"name": "Регистрация", "points": 10},
    "morning_routine": {"name": "Утренний опрос", "points": 10},
    "log_filled": {"name": "Дневник заполнен", "points": 5},
    "cycle_honest": {"name": "Честный цикл", "points": 15},
    "sos_used": {"name": "SOS самопомощь", "points": 5},
    "sos_pro_used": {"name": "SOS психолог", "points": -50},
    "meditation": {"name": "Медитация", "points": 10},
    "hiit_done": {"name": "HIIT выполнен", "points": 20},
    "water_glass": {"name": "Вода выпита", "points": 1},
}

# ==================== КЛАСС ГЕЙМИФИКАЦИИ ====================
class GamificationSystem:
    def __init__(self, db_connection):
        self.db = db_connection
        print("✅ GamificationSystem инициализирована")
    
    def get_title(self, points: int, gender: int) -> dict:
        """Получить текущее звание по очкам и полу"""
        titles = FEMALE_TITLES if gender == 1 else MALE_TITLES
        for title in titles:
            if title["min"] <= points <= title["max"]:
                return title
        return titles[-1]
    
    def add_points(self, user_id: int, action_key: str) -> dict:
        """Начислить очки за действие"""
        if action_key not in ACTIONS:
            return {'error': 'Unknown action', 'points_added': 0}
        
        action = ACTIONS[action_key]
        
        try:
            with self.db:
                cur = self.db.cursor()
                cur.execute(
                    "SELECT bio_points, gender_type, achievements FROM users WHERE user_id = ?", 
                    (user_id,)
                )
                user = cur.fetchone()
            
            if not user:
                return {'error': 'User not found', 'points_added': 0}
            
            points, gender, achievements_json = user
            achievements = json.loads(achievements_json) if achievements_json else []
            
            new_points = points + action['points']
            
            # Проверяем на отрицательные очки
            if new_points < 0:
                new_points = 0
            
            # Обновляем очки
            cur.execute(
                "UPDATE users SET bio_points = ? WHERE user_id = ?", 
                (new_points, user_id)
            )
            
            # Проверяем новые достижения
            new_achievements = []
            
            # Проверяем первое действие
            if action_key == "first_blood" and "first_blood" not in achievements:
                achievements.append("first_blood")
                new_achievements.append(ACHIEVEMENTS["first_blood"])
            
            # Проверяем достижения по очкам
            if new_points >= 100 and "century" not in achievements:
                achievements.append("century")
                new_achievements.append(ACHIEVEMENTS["century"])
            
            if new_points >= 500 and "half_k" not in achievements:
                achievements.append("half_k")
                new_achievements.append(ACHIEVEMENTS["half_k"])
            
            if new_points >= 1000 and "grand" not in achievements:
                achievements.append("grand")
                new_achievements.append(ACHIEVEMENTS["grand"])
            
            # Сохраняем достижения
            if new_achievements:
                cur.execute(
                    "UPDATE users SET achievements = ? WHERE user_id = ?",
                    (json.dumps(achievements), user_id)
                )
            
            self.db.commit()
            
            # Проверяем новое звание
            old_title = self.get_title(points, gender)
            new_title = self.get_title(new_points, gender)
            title_changed = old_title['name'] != new_title['name']
            
            return {
                'points_added': action['points'],
                'total_points': new_points,
                'new_title': new_title if title_changed else None,
                'new_achievements': new_achievements
            }
            
        except Exception as e:
            print(f"Ошибка при начислении очков: {e}")
            return {'error': str(e), 'points_added': 0}
    
    def format_profile(self, user_id: int) -> str:
        """Форматировать профиль пользователя для вывода"""
        try:
            with self.db:
                cur = self.db.cursor()
                cur.execute("""
                    SELECT power_name, bio_points, gender_type, achievements 
                    FROM users WHERE user_id = ?
                """, (user_id,))
                user = cur.fetchone()
            
            if not user:
                return "❌ Пользователь не найден"
            
            name, points, gender, achievements_json = user
            achievements = json.loads(achievements_json) if achievements_json else []
            title = self.get_title(points, gender)
            
            text = f"🎮 **ПРОФИЛЬ БИОХАКЕРА**\n\n"
            text += f"{title['emoji']} **{title['name']}**\n"
            text += f"{title['desc']}\n\n"
            text += f"⭐ **Очки биохакера:** {points}\n\n"
            
            if achievements:
                text += "🏆 **Достижения:**\n"
                # Показываем последние 5 достижений
                shown = 0
                for ach_key in achievements:
                    if shown >= 5:
                        break
                    if ach_key in ACHIEVEMENTS:
                        ach = ACHIEVEMENTS[ach_key]
                        text += f"{ach['emoji']} {ach['name']}\n"
                        shown += 1
                
                if len(achievements) > 5:
                    text += f"... и еще {len(achievements) - 5}\n"
            
            # Добавляем информацию о следующем звании
            next_title = None
            titles = FEMALE_TITLES if gender == 1 else MALE_TITLES
            for i, t in enumerate(titles):
                if t['name'] == title['name'] and i < len(titles) - 1:
                    next_title = titles[i + 1]
                    break
            
            if next_title:
                need = next_title['min'] - points
                text += f"\n🎯 До следующего звания: **{need}** ⭐"
                text += f"\n{next_title['emoji']} {next_title['name']}"
            
            return text
            
        except Exception as e:
            return f"❌ Ошибка при формировании профиля: {e}"


# ==================== ФУНКЦИИ ДЛЯ ЛИДЕРБОРДА ====================
def get_leaderboard(db, limit=10):
    """Получить топ пользователей по очкам"""
    try:
        cur = db.cursor()
        cur.execute("""
            SELECT power_name, bio_points, gender_type 
            FROM users 
            WHERE bio_points > 0 
            ORDER BY bio_points DESC 
            LIMIT ?
        """, (limit,))
        
        leaders = []
        
        for row in cur.fetchall():
            name, points, gender = row
            title_list = FEMALE_TITLES if gender == 1 else MALE_TITLES
            current_title = title_list[0]
            for t in title_list:
                if t["min"] <= points <= t["max"]:
                    current_title = t
                    break
            leaders.append({
                'name': name,
                'points': points,
                'title': current_title['name'],
                'emoji': current_title['emoji']
            })
        
        return leaders
    except Exception as e:
        print(f"Ошибка при получении лидерборда: {e}")
        return []


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================
def get_user_stats(user_id: int) -> dict:
    """Получить статистику пользователя"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            
            stats = {
                'morning_count': 0,
                'evening_count': 0,
                'water_count': 0,
                'hiit_count': 0,
                'streak': 0,
                'last_activity': None
            }
            
            # Утренние замеры
            cur.execute("SELECT COUNT(*) as count FROM morning_checkin WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            stats['morning_count'] = row['count'] if row else 0
            
            # Вечерние аудиты
            cur.execute("SELECT COUNT(*) as count FROM evening_audit WHERE user_id = ?", (user_id,))
            row = cur.fetchone()
            stats['evening_count'] = row['count'] if row else 0
            
            # HIIT (из evening_audit)
            cur.execute("SELECT COUNT(*) as count FROM evening_audit WHERE user_id = ? AND hiit_done = 1", (user_id,))
            row = cur.fetchone()
            stats['hiit_count'] = row['count'] if row else 0
            
            # Вода (из water_logs)
            try:
                cur.execute("SELECT COUNT(*) as count FROM water_logs WHERE user_id = ?", (user_id,))
                row = cur.fetchone()
                stats['water_count'] = row['count'] if row else 0
            except:
                stats['water_count'] = 0
            
            # Последняя активность
            cur.execute("""
                SELECT MAX(date) as last_date FROM (
                    SELECT date FROM morning_checkin WHERE user_id = ?
                    UNION
                    SELECT date FROM evening_audit WHERE user_id = ?
                )
            """, (user_id, user_id))
            row = cur.fetchone()
            stats['last_activity'] = row['last_date'] if row else None
            
            # Серия (упрощенно)
            if stats['last_activity']:
                last = date.fromisoformat(stats['last_activity'])
                today = date.today()
                if (today - last).days <= 1:
                    stats['streak'] = 1  # тут нужна более сложная логика
            
            return stats
            
    except Exception as e:
        print(f"Ошибка при получении статистики: {e}")
        return {}


print("✅ Все функции gamification.py загружены")
print("🔥🔥🔥 GAMIFICATION.PY ЗАГРУЗКА ЗАВЕРШЕНА 🔥🔥🔥")

# ==================== ЭКСПОРТ ====================
__all__ = [
    'GamificationSystem', 
    'get_leaderboard', 
    'get_user_stats',
    'ACHIEVEMENTS', 
    'ACTIONS',
    'FEMALE_TITLES',
    'MALE_TITLES'
]
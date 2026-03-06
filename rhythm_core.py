# rhythm_core.py - ОПТИМИЗИРОВАННАЯ ВЕРСИЯ
"""
Мастер-таблица ритмов "КОД РЕВЕРС" - только доказанные циклы + HIIT
"""
import datetime
from typing import Dict, Any, Tuple, List

print("🔥 RHYTHM_CORE.PY ЗАГРУЖАЕТСЯ 🔥")

# === ЖЕНСКИЙ ЦИКЛ (ДЕТАЛЬНАЯ ВЕРСИЯ) ===
FEMALE_PHASES_DETAIL = {
    1: {
        "name": "Менструация",
        "description": "Фаза покоя. Вязкость лимфы ↑, pH падает.",
        "hormones": "Эстроген ↓↓, Прогестерон ↓↓",
        "load": "ОТДЫХ. Только легкая растяжка. Вакуум живота.",
        "nutrition": "Исключить сахар и кофеин. Железо + Вит. С.",
        "energy": 0.2,
        "emoji": "🌸",
        "hiit_block": True
    },
    2: {
        "name": "Фолликулярная",
        "description": "Рост энергии. Текучесть лимфы ↑. Пик синтеза белка.",
        "hormones": "Эстроген ↑↑, Тестостерон ↑",
        "load": "УМСТВЕННЫЙ ШТУРМ. Изучение нового, логика.",
        "nutrition": "Увеличить качественный белок.",
        "energy": 0.8,
        "emoji": "🌱",
        "hiit_block": False
    },
    3: {
        "name": "Овуляция",
        "description": "Пик формы. Макс. метаболизм. Выносливость на пике.",
        "hormones": "Эстроген (Пик), Тестостерон (Пик)",
        "load": "ФИЗИЧЕСКИЙ ПИК. HIIT, тяжелые переговоры.",
        "nutrition": "Сложные углеводы (гречка, овощи).",
        "energy": 1.0,
        "emoji": "⚡",
        "hiit_block": False,
        "hiit_double": True
    },
    4: {
        "name": "Лютеиновая",
        "description": "Стабилизация. Завершение дел.",
        "hormones": "Прогестерон ↑↑, Эстроген ↓",
        "load": "ВНИМАТЕЛЬНОСТЬ. Отчеты, мягкая нагрузка.",
        "nutrition": "Магний (400–600 мг).",
        "energy": 0.6,
        "emoji": "🌿",
        "hiit_block": False
    },
    5: {
        "name": "ПМС/Детокс",
        "description": "Критическая зона. Отечность ↑. Накопление Na.",
        "hormones": "Прогестерон ↑, Эстроген ↓",
        "load": "КОНТРОЛЬ. Только мягкий лимфодренаж.",
        "nutrition": "МИНИМУМ СОЛИ. Калий (авокадо, курага).",
        "energy": 0.3,
        "emoji": "🍂",
        "hiit_block": True
    }
}

# === 9-ДНЕВНЫЙ ЦИКЛ ЦНС ===
CNS_PHASES = {
    1: {"name": "ЗАПУСК", "energy": 0.7, "load": "Средняя (70%)", "desc": "Адаптация к нагрузкам"},
    2: {"name": "ПИК А", "energy": 1.0, "load": "Максимальная (100%)", "desc": "Пик физической формы"},
    3: {"name": "ПЛАТО", "energy": 0.9, "load": "Высокая (90%)", "desc": "Стабильно высокая активность"},
    4: {"name": "БУФЕР", "energy": 0.5, "load": "Умеренная (50%)", "desc": "Смена ритма, облегченный день"},
    5: {"name": "ПИК Б", "energy": 1.0, "load": "Максимальная (100%)", "desc": "Вторая волна энергии"},
    6: {"name": "СТАБИЛЬНОСТЬ", "energy": 0.8, "load": "Высокая (80%)", "desc": "Закрепление результатов"},
    7: {"name": "ДЕТОКС", "energy": 0.3, "load": "Низкая (20%)", "desc": "Очищение организма"},
    8: {"name": "ДУША", "energy": 0.2, "load": "Минимальная (10%)", "desc": "Активный отдых, хобби"},
    9: {"name": "ТИШИНА", "energy": 0.1, "load": "Отдых (0%)", "desc": "Полное восстановление"}
}

# === HIIT ПРОТОКОЛЫ ===
HIIT_PROTOCOLS = {
    "menstrual": {
        "name": "ФАЗА ПОКОЯ",
        "duration": "15-20 мин",
        "type": "🧘 Йога/Растяжка",
        "protocol": "• Никакого HIIT\n• Сурья Намаскар (плавно)\n• Дыхательные практики",
        "days": (1, 5)
    },
    "follicular": {
        "name": "ФАЗА ЖИРОСЖИГАНИЯ",
        "duration": "25 мин",
        "type": "⚡ Интервальный HIIT",
        "protocol": "• 5 мин разминка\n• 15 мин HIIT (30/30)\n• 5 мин заминка",
        "days": (6, 12)
    },
    "ovulation": {
        "name": "ФАЗА ПИК",
        "duration": "30 мин",
        "type": "🔥 Смешанный HIIT",
        "protocol": "• 5 мин разминка\n• 20 мин HIIT (40/20)\n• 5 мин силовая",
        "days": (13, 16)
    },
    "luteal": {
        "name": "ФАЗА ТОНУСА",
        "duration": "25 мин",
        "type": "💪 Силовой HIIT",
        "protocol": "• 5 мин разминка\n• 15 мин силовые интервалы\n• 5 мин растяжка",
        "days": (17, 24)
    },
    "premenstrual": {
        "name": "ФАЗА ВОССТАНОВЛЕНИЯ",
        "duration": "15-20 мин",
        "type": "🧘 Мягкая активность",
        "protocol": "• 5 мин разминка\n• 10 мин легкое кардио\n• 5 мин растяжка",
        "days": (25, 28)
    }
}

# === ОСНОВНЫЕ ФУНКЦИИ ===

def get_female_phase(day: int, cycle_length: int = 28) -> dict:
    """
    Возвращает словарь с данными о фазе женского цикла
    """
    if 1 <= day <= 5:
        return FEMALE_PHASES_DETAIL[1]
    elif 6 <= day <= 12:
        return FEMALE_PHASES_DETAIL[2]
    elif 13 <= day <= 16:
        return FEMALE_PHASES_DETAIL[3]
    elif 17 <= day <= 24:
        return FEMALE_PHASES_DETAIL[4]
    else:  # 25-28
        return FEMALE_PHASES_DETAIL[5]


def get_female_phase_simple(day: int, cycle_length: int = 28) -> Tuple[str, str, str]:
    """
    Упрощенная версия для совместимости.
    Возвращает кортеж (название, описание, рекомендация)
    """
    phase = get_female_phase(day, cycle_length)
    return (phase["name"], phase["description"], phase["load"])


def get_cns_phase(day: int) -> dict:
    """
    Возвращает словарь с данными о фазе ЦНС
    """
    return CNS_PHASES.get(day, CNS_PHASES[1])


def get_cns_phase_simple(day: int) -> Tuple[str, str, str]:
    """
    Упрощенная версия для совместимости.
    Возвращает кортеж (название, нагрузка, описание)
    """
    phase = get_cns_phase(day)
    return (phase["name"], phase["load"], phase["desc"])


def get_combined_recommendation(female_day: int, cns_day: int, cycle_length: int = 28) -> dict:
    """
    Объединяет рекомендации женского цикла и ЦНС
    """
    female = get_female_phase(female_day, cycle_length)
    cns = get_cns_phase(cns_day)
    
    base_energy = female["energy"]
    cns_multiplier = cns["energy"]
    final_energy = max(0.1, min(1.0, base_energy * cns_multiplier))
    
    # Определяем рекомендацию по нагрузке
    if female.get("hiit_block", False):
        load_recommendation = "🔥 ПОЛНЫЙ ОТДЫХ. Только мягкая растяжка."
    elif final_energy < 0.3:
        load_recommendation = "🔥 ПОЛНЫЙ ОТДЫХ. Только мягкая растяжка."
    elif final_energy < 0.5:
        load_recommendation = "🧘 ЛЕГКАЯ АКТИВНОСТЬ. Йога, прогулка."
    elif final_energy < 0.7:
        load_recommendation = "🏃‍♀️ СРЕДНЯЯ НАГРУЗКА. Можно тренироваться, но без рекордов."
    else:
        if female.get("hiit_double", False) and cns["energy"] > 0.8:
            load_recommendation = "🚀 ДВОЙНОЙ HIIT! Пик формы!"
        else:
            load_recommendation = female["load"]
    
    return {
        "female_phase": female["name"],
        "female_desc": female["description"],
        "cns_phase": cns["name"],
        "cns_desc": cns["desc"],
        "energy": round(final_energy * 100),  # в процентах
        "load": load_recommendation,
        "nutrition": female["nutrition"],
        "hormones": female.get("hormones", "Нет данных"),
        "hiit_allowed": not female.get("hiit_block", False) and final_energy >= 0.5
    }


def get_hiit_protocol(female_day: int, cycle_length: int = 28) -> dict:
    """
    Возвращает протокол HIIT по дню цикла
    """
    for protocol in HIIT_PROTOCOLS.values():
        start, end = protocol["days"]
        if start <= female_day <= end:
            return protocol
    return HIIT_PROTOCOLS["premenstrual"]


def get_hiit_recommendation(user_data: dict) -> str:
    """
    Полная рекомендация по HIIT для женщины
    """
    today = datetime.date.today()
    cycle_start = datetime.date.fromisoformat(user_data['cycle_start'])
    cycle_length = user_data.get('cycle_length', 28)
    female_day = (today - cycle_start).days % cycle_length + 1
    
    protocol = get_hiit_protocol(female_day, cycle_length)
    
    text = f"🔥 **HIIT ПРОТОКОЛ**\n\n"
    text += f"📅 **Фаза:** {protocol['name']}\n"
    text += f"⏱️ **Длительность:** {protocol['duration']}\n"
    text += f"💪 **Тип:** {protocol['type']}\n\n"
    text += f"**Протокол:**\n{protocol['protocol']}\n"
    
    return text


def calculate_fat_burn_window(female_day: int, wake_time: str) -> list:
    """
    Рассчитывает лучшее время для жиросжигания
    """
    hour = int(wake_time.split(':')[0])
    
    windows = [
        {
            'time': f"{hour:02d}:30 - {(hour+1):02d}:00",
            'type': '🌅 Утреннее жиросжигание',
            'efficiency': '⚡ Высокая',
            'note': 'Натощак - жир горит максимально'
        },
        {
            'time': f"{(hour+4):02d}:00 - {(hour+5):02d}:00",
            'type': '☀️ Дневное окно',
            'efficiency': '🟡 Средняя',
            'note': 'Через 2 часа после еды'
        },
        {
            'time': f"{(hour+9):02d}:00 - {(hour+10):02d}:00",
            'type': '🌆 Вечернее окно',
            'efficiency': '🟢 Хорошая',
            'note': 'За 3-4 часа до сна'
        }
    ]
    
    # Корректировка в зависимости от фазы цикла
    if 1 <= female_day <= 5:
        windows[0]['note'] += ' (в менструацию только легкая активность)'
    elif 13 <= female_day <= 16:
        windows[0]['efficiency'] = '⚡⚡ МАКСИМАЛЬНАЯ'
    
    return windows


# ==================== ВОПРОСЫ ДЛЯ ДНЕВНИКА ====================
DAILY_LOG_QUESTIONS = [
    {
        "category": "Ментальное состояние",
        "questions": [
            {"key": "motivation", "text": "Мотивация (1-5)?", "min": 1, "max": 5},
            {"key": "stress", "text": "Уровень стресса (1-5, где 1 - дзен, 5 - паника)?", "min": 1, "max": 5},
        ]
    },
    {
        "category": "Пищеварение",
        "questions": [
            {"key": "heaviness", "text": "Тяжесть после еды? (1-5)", "min": 1, "max": 5},
            {"key": "sugar_craving", "text": "Тяга к сладкому? (1-5)", "min": 1, "max": 5}
        ]
    },
    {
        "category": "Энергия",
        "questions": [
            {"key": "energy", "text": "Общая энергия? (1-5)", "min": 1, "max": 5},
            {"key": "swelling", "text": "Отечность утром? (1-5)", "min": 1, "max": 5}
        ]
    }
]

# ==================== ВОПРОСЫ ДЛЯ ВЕЧЕРНЕГО ОПРОСА ====================
AUDIT_QUESTIONS = [
    "Питание: соблюдал(а) ли окна? (1-5)",
    "Осознанность в еде? (1-5)",
    "Выполнил(а) ли физ. нагрузку? (1-5)",
    "Уровень мотивации сегодня? (1-5)",
    "Общее самочувствие? (1-5)",
    "Эмоциональная стабильность? (1-5)"
]


def get_daily_protocol(user: dict) -> str:
    """
    Формирует дневной протокол для пользователя
    (Дубликат из bot.py для совместимости)
    """
    from datetime import date
    
    if not user:
        return "❌ Пользователь не найден"
    
    today = date.today()
    
    # Получаем день ЦНС
    rhythm_start = date.fromisoformat(user['rhythm_start'])
    cns_day = (today - rhythm_start).days % 9 + 1
    cns_data = get_cns_phase(cns_day)
    
    # Базовая информация
    result = f"🧬 **{user.get('power_name', '')}, твой статус на сегодня:**\n\n"
    result += f"🧠 **ЦНС:** День {cns_day} — {cns_data['name']}\n"
    result += f"📊 {cns_data['desc']}\n\n"
    
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
    
    return result


print("✅ Все функции rhythm_core.py загружены")
print("🔥🔥🔥 RHYTHM_CORE.PY ЗАГРУЗКА ЗАВЕРШЕНА 🔥🔥🔥")

# ==================== ЭКСПОРТ ====================
__all__ = [
    'get_female_phase',
    'get_female_phase_simple',
    'get_cns_phase',
    'get_cns_phase_simple',
    'get_combined_recommendation',
    'get_hiit_protocol',
    'get_hiit_recommendation',
    'calculate_fat_burn_window',
    'get_daily_protocol',
    'DAILY_LOG_QUESTIONS',
    'AUDIT_QUESTIONS',
    'FEMALE_PHASES_DETAIL',
    'CNS_PHASES',
    'HIIT_PROTOCOLS'
]
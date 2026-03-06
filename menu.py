# menu.py
print("🔥 MENU.PY ЗАГРУЖАЕТСЯ 🔥")

from aiogram import types, F, Router
from aiogram.fsm.context import FSMContext
from aiogram.utils.keyboard import ReplyKeyboardBuilder, InlineKeyboardBuilder
from datetime import date, datetime, timedelta
import sqlite3
import json

from mindful_eating import start_mindful_eating


from texts import BotTexts
from utils import get_user, update_user_db, check_rate_limit, has_access

from datetime import datetime, date, timedelta
import pytz
from gamification import FEMALE_TITLES, MALE_TITLES

from aiogram import Router
water_router = Router()

# Импортируем из rhythm_core, но не get_daily_protocol (его нет там)
from rhythm_core import (
    get_cns_phase, get_female_phase, 
    get_combined_recommendation, get_hiit_recommendation,
    get_hiit_protocol, calculate_fat_burn_window
)

# ВАЖНО: называем роутер по-другому
menu_router = Router()

print("✅ Импорты в menu.py выполнены")

# ==================== ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ДНЕВНОГО ПРОТОКОЛА ====================
def get_daily_protocol(user: dict) -> str:
    """Получить персональную рекомендацию с учетом всех циклов (дубликат из bot.py)"""
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

# ==================== ГЛАВНОЕ МЕНЮ ====================
async def show_main_menu(message: types.Message):
    """Главное меню (всегда видно)"""
    user = get_user(message.from_user.id)
    
    kb = ReplyKeyboardBuilder()
    
    # Базовые кнопки для всех
    kb.button(text="🚀 Дневной режим")
    kb.button(text="🧬 Мои протоколы")
    kb.button(text="🍎 Питание")
    kb.button(text="💧 ВОДА")
        
    # Кнопка для женщин с циклом (гендер = 1)
    if user and user.get('gender_type') == 1:
        kb.button(text="🩸 НАЧАЛИСЬ МЕСЯЧНЫЕ")  # 👈 ТОЛЬКО ДЛЯ ЖЕНЩИН С ЦИКЛОМ
    
    kb.button(text="🧬 Генетика")
    kb.button(text="⚡️ Начинаю работу")
    kb.button(text="📊 Моя статистика")
    kb.button(text="📈 Прогноз энергии")
    kb.button(text="🔄 Анализ рисков")
    kb.button(text="🆘 SOS / Срыв")
    kb.button(text="🎉 Код свобода")
    kb.button(text="⚙️ Настройки")
    kb.button(text="💳 Подписка")
    
    await message.answer(
        "📋 **Главное меню**\nВыбери раздел:",
        reply_markup=kb.adjust(3).as_markup(resize_keyboard=True)
    )

print("✅ Функция show_main_menu определена")

# ==================== ОБРАБОТЧИКИ ====================

@menu_router.message(F.text == "🩸 НАЧАЛИСЬ МЕСЯЧНЫЕ")
async def period_reset_handler(message: types.Message):
    """Сброс цикла при начале месячных"""
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    if user['gender_type'] != 1:
        return await message.answer("❌ Эта функция доступна только для женщин с циклом.")
    
    today = date.today()
    new_cycle_start = today.isoformat()
    new_rhythm_start = (today + timedelta(days=5)).isoformat()
    
    update_user_db(message.from_user.id, {
        'cycle_start': new_cycle_start,
        'rhythm_start': new_rhythm_start
    })
    
    await message.answer("✅ **Цикл сброшен!**\n\n"
                        "Новый цикл начат сегодня.\n"
                        "Ритм ЦНС перестроен.\n"
                        "Следующие 5 дней — лёгкий режим.")
    
    await award_points(message.from_user.id, "cycle_honest", message)
    
    user = get_user(message.from_user.id)
    await message.answer(get_daily_protocol(user))


@menu_router.message(F.text == "🚀 ДНЕВНОЙ РЕЖИМ")
async def daily_mode_handler(message: types.Message, state: FSMContext):
    """Показать дневной протокол"""
    allowed, msg = await check_rate_limit(message.from_user.id)
    if not allowed:
        return await message.answer(msg)
    
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    protocol = get_daily_protocol(user)
    await message.answer(protocol)
    
    # Получаем часовой пояс пользователя
    user_tz = user.get('tz', 'Europe/Moscow')
    try:
        import pytz
        tz = pytz.timezone(user_tz)
        now = datetime.now(tz)
        current_hour = now.hour
        
        # Получаем время пробуждения пользователя
        wake_time = user.get('wake_time', '07:00')
        wake_hour = int(wake_time.split(':')[0])
        
        # Если сейчас до времени пробуждения + 2 часа
        if current_hour < wake_hour + 2:
            # Кнопка для утреннего опроса
            kb = InlineKeyboardBuilder()
            kb.button(text="🚀 Я проснулся", callback_data="wake_up")
            await message.answer(
                f"🌅 Доброе утро! (по твоему времени {now.strftime('%H:%M')})\n"
                f"Готов(а) начать день?",
                reply_markup=kb.as_markup()
            )
        else:
            # После 2 часов после пробуждения показываем другое сообщение
            await message.answer(
                f"🌞 Уже {now.strftime('%H:%M')} по твоему времени.\n"
                f"Если ты не сделал(а) утренний опрос, лучше сделать его завтра утром.\n\n"
                f"А пока можешь посмотреть свой дневной протокол выше или выбрать другой раздел меню."
            )
    except:
        # Если ошибка с часовым поясом, используем UTC
        now = datetime.now()
        current_hour = now.hour
        if current_hour < 9:
            kb = InlineKeyboardBuilder()
            kb.button(text="🚀 Я проснулся", callback_data="wake_up")
            await message.answer(
                "🌅 Доброе утро! Готов(а) начать день?",
                reply_markup=kb.as_markup()
            )
        else:
            await message.answer(
                "🌞 Уже день! Если ты не сделал(а) утренний опрос, лучше сделать его завтра утром."
            )


@menu_router.message(F.text == "🧬 МОИ ПРОТОКОЛЫ")
async def protocols_menu(message: types.Message):
    """Меню протоколов"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🧠 ЦНС сегодня", callback_data="cns_today")
    kb.button(text="🩸 Цикл сегодня", callback_data="cycle_today")
    kb.button(text="⚡ HIIT сегодня", callback_data="hiit_today")
    kb.button(text="💊 БАДы сегодня", callback_data="supplements_today")
    kb.button(text="🧬 Генетика", callback_data="genetics_quick")
    kb.button(text="🌙 Лунный календарь", callback_data="lunar_info")
    kb.adjust(1)
    
    await message.answer(
        "📋 **Выбери протокол:**",
        reply_markup=kb.as_markup()
    )


@menu_router.message(F.text == "🍎 ПИТАНИЕ")
async def nutrition_menu(message: types.Message):
    """Меню питания"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🍳 Завтрак", callback_data="nutrition_breakfast")
    kb.button(text="🥗 Обед", callback_data="nutrition_lunch")
    kb.button(text="🌱 Ужин", callback_data="nutrition_dinner")
    kb.button(text="🍽️ РЕЖИМ ЕДЫ", callback_data="mindful_eating")  # 👈 ЭТО ВАЖНО!
    kb.button(text="📋 Мои рецепты", callback_data="my_recipes")
    kb.adjust(2, 2, 1)
    
    await message.answer(
        "🥑 **Выбери раздел питания:**",
        reply_markup=kb.as_markup()
    )


@menu_router.message(F.text == "💧 ВОДА")
async def water_menu(message: types.Message):
    """Водный модуль"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    from water_calculator import WaterCalculator
    import json
    
    # Получаем данные пользователя
    user_data = {
        'weight': user.get('weight', 70),
        'daily_protein': user.get('daily_protein', 70),
        'genetics_fto': user.get('genetics_fto', ''),
        'gender_type': user.get('gender_type'),
        'cycle_start': user.get('cycle_start'),
        'cycle_length': user.get('cycle_length', 28),
        'water_consumed_today': user.get('water_consumed_today', 0),
        'activity_minutes': user.get('activity_minutes', 0)  # можно добавить в регистрацию
    }
    
    # Сохраняем норму, если еще нет
    if not user.get('water_goal'):
        total = WaterCalculator.calculate_total(user_data)
        schedule = WaterCalculator.get_schedule(total)
        water_plan = {'total': total, 'schedule': schedule}
        
        update_user_db(message.from_user.id, {
            'water_goal': total,
            'water_preferences': json.dumps(water_plan, ensure_ascii=False)
        })
    else:
        total = user.get('water_goal')
    
    # Формируем отчет
    user_data['water_goal'] = total
    report = WaterCalculator.format_report(user_data)
    
    # Кнопки
    kb = InlineKeyboardBuilder()
    kb.button(text="💧 +250 мл", callback_data="water_log")
    kb.button(text="📅 Расписание", callback_data="water_schedule")
    kb.button(text="🧠 Как считается?", callback_data="water_explain")
    kb.adjust(2)
    
    await message.answer(report, reply_markup=kb.as_markup())


@menu_router.message(F.text == "🍽️ РЕЖИМ ЕДЫ")
async def eating_mode_start(message: types.Message, state: FSMContext):
    """Запуск осознанного питания"""
    print("="*50)
    print(f"🍽️ НАЖАТА КНОПКА РЕЖИМА ЕДЫ")
    print(f"📌 ID в menu.py: {message.from_user.id}")
    print(f"📱 User ID: {message.from_user.id}")
    print(f"👤 Username: {message.from_user.username}")
    
    # Проверяем пользователя
    from utils import get_user
    user = get_user(message.from_user.id)
    
    if not user:
        print(f"❌ Пользователь {message.from_user.id} НЕ НАЙДЕН!")
        return await message.answer("Сначала пройди регистрацию: /start")
    
    print(f"✅ Пользователь {message.from_user.id} найден: {user.get('power_name')}")
    print(f"🔍 Вызываю start_mindful_eating...")
    
    from mindful_eating import start_mindful_eating
    await start_mindful_eating(message, state)
    
    print(f"✅ start_mindful_eating вызвана")
    print("="*50)

@menu_router.message(F.text == "🧬 Генетика")
async def genetics_menu(message: types.Message, state: FSMContext):
    """Генетический модуль"""
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
    
    # Если уже есть данные, показываем их
    if user.get('genetics_mthfr'):
        # Функция generate_genetics_report должна быть импортирована из bot.py
        # или определена здесь
        try:
            from bot import generate_genetics_report
            result = generate_genetics_report(
                user.get('genetics_mthfr', ''),
                user.get('genetics_fto', ''),
                user.get('genetics_actn3', '')
            )
            await message.answer(result)
        except:
            # Если не получается импортировать, показываем упрощенный вариант
            text = "🧬 **Твои генетические данные:**\n\n"
            text += f"MTHFR: {user.get('genetics_mthfr', 'не указано')}\n"
            text += f"FTO: {user.get('genetics_fto', 'не указано')}\n"
            text += f"ACTN3: {user.get('genetics_actn3', 'не указано')}\n\n"
            text += "Подробный отчет доступен в боте."
            await message.answer(text)
    else:
        # Иначе предлагаем ввести
        kb = InlineKeyboardBuilder()
        kb.button(text="📤 Загрузить файл", callback_data="genetics_file")
        kb.button(text="✏️ Ввести вручную", callback_data="genetics_manual")
        kb.button(text="⏩ Позже", callback_data="genetics_skip")
        
        await message.answer(
            "🧬 **Генетический паспорт здоровья**\n\n"
            "У тебя еще нет данных. Выбери способ ввода:",
            reply_markup=kb.as_markup()
        )
        # В bot.py это состояние Reg.genetics_consent
        # Но мы не можем импортировать Reg из bot.py из-за циклических импортов
        # Поэтому используем строку
        await state.set_state("genetics_consent")


@menu_router.message(F.text == "📊 ПРОГРЕСС")
async def progress_menu(message: types.Message):
    """Меню прогресса"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 Утренние замеры", callback_data="stats_morning")
    kb.button(text="🌙 Вечерние аудиты", callback_data="stats_evening")
    kb.button(text="📏 Недельные замеры", callback_data="stats_weekly")
    kb.button(text="🏆 Достижения", callback_data="achievements")
    kb.button(text="⭐ Мои очки", callback_data="my_points")
    kb.adjust(2, 2, 1)
    
    await message.answer(
        "📊 **Статистика и прогресс:**",
        reply_markup=kb.as_markup()
    )

@menu_router.message(F.text == "📊 МОЯ СТАТИСТИКА")
async def statistics_menu_handler(message: types.Message):
    """Обработчик кнопки статистики"""
    from statistics import show_statistics_menu
    await show_statistics_menu(message)

@menu_router.message(F.text == "🆘 SOS / СРЫВ")
async def sos_menu(message: types.Message):
    """SOS меню"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🍬 Тянет на сладкое", callback_data="sos_sugar")
    kb.button(text="😰 Тревога/стресс", callback_data="sos_stress")
    kb.button(text="😴 Упадок сил", callback_data="sos_fatigue")
    kb.button(text="🍽️ Срыв/переедание", callback_data="sos_binge")
    kb.button(text="📞 Психолог", callback_data="call_psychologist")
    kb.adjust(1)
    
    await message.answer(
        "🆘 **Что случилось?**\nВыбери ситуацию:",
        reply_markup=kb.as_markup()
    )

@menu_router.message(F.text == "📈 ПРОГНОЗ ЭНЕРГИИ")
async def energy_forecast_menu(message: types.Message):
    """Показать прогноз энергии с учетом типа женщины"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    from energy_forecast import EnergyForecast, check_future_critical, get_future_warning_message
    
    try:
        forecast = EnergyForecast(user)
        month = forecast.get_month_forecast()
        
        # 👇 ОПРЕДЕЛЯЕМ ТИП ЖЕНЩИНЫ
        gender = user.get('gender_type')
        age = user.get('age', 45)  # нужно добавить возраст в регистрацию
        
        # Получаем прогноз в зависимости от типа
        if gender == 1:  # женщина с циклом
            week = forecast.get_week_forecast()
            forecast_type = "cycle"
        else:  # женщина без цикла
            # Создаем прогноз вручную для женщин без цикла
            from datetime import timedelta
            week = []
            for i in range(7):
                day = date.today() + timedelta(days=i)
                energy_data = forecast.get_daily_energy_no_cycle(day)
                week.append(energy_data)
            forecast_type = "no_cycle"
        
        # Проверяем критические периоды
        warning = check_future_critical(month)
        if warning['has_critical']:
            warning_message = get_future_warning_message(month)
            await message.answer(warning_message)
        
        # Анализируем текущий день
        today_energy = week[0]['energy']
        tomorrow_energy = week[1]['energy'] if len(week) > 1 else None
        
        # Срочные рекомендации
        urgent_advice = ""
        if today_energy < 30:
            urgent_advice = """
🚨 **СРОЧНО! ТВОЯ ЭНЕРГИЯ СЕГОДНЯ КРИТИЧЕСКАЯ!**

❌ НЕ ДЕЛАЙ:
• Никаких тренировок
• Никаких важных решений
• Никакого самобичевания

✅ ЧТО ДЕЛАТЬ:
• Только отдых и восстановление
• Теплые бульоны
• Горячая ванна с магнием
• Сон 9+ часов
"""
        elif today_energy < 40:
            urgent_advice = """
😴 **СЕГОДНЯ НИЗКАЯ ЭНЕРГИЯ**
• Только прогулки и легкая активность
• Легкая еда, много воды
• Лечь спать пораньше
"""
        elif today_energy >= 70:
            urgent_advice = """
⚡ **СЕГОДНЯ ХОРОШАЯ ЭНЕРГИЯ!**
• Можно делать дела
• Умеренные тренировки
"""
        
        # Основной прогноз
        text = "📈 **ТВОЙ ПРОГНОЗ ЭНЕРГИИ**\n\n"
        
        # Добавляем информацию о типе
        if forecast_type == "no_cycle":
            if age >= 50:
                text += "🌙 **Менопауза** — энергия стабильная, но с волнами\n\n"
            elif age >= 40:
                text += "🌸 **Пременопауза** — возможны перепады\n\n"
        
        for i, day in enumerate(week):
            if day['energy'] >= 70:
                emoji = "🔴"
            elif day['energy'] >= 50:
                emoji = "🟡"
            elif day['energy'] >= 35:
                emoji = "🟢"
            else:
                emoji = "🔵"
            
            day_text = f"{emoji} **{day['date'].strftime('%d.%m')}:** {day['energy']}%"
            
            if i == 0:
                day_text += " ← СЕГОДНЯ"
            elif i == 1:
                day_text += " ← ЗАВТРА"
            
            text += day_text + "\n"
        
        # Добавляем специальные протоколы для женщин без цикла
        if forecast_type == "no_cycle":
            if age >= 50:
                text += """

🌙 **ПРОТОКОЛ ДЛЯ МЕНОПАУЗЫ (50+):**
• Костный бульон ежедневно
• Омега-3 2-3 г/день
• Витамин D3 2000-5000 МЕ
• Магний 400 мг на ночь
• Кальций с K2 (для костей)
• HIIT заменяем на силовые и прогулки
"""
            elif age >= 40:
                text += """

🌸 **ПРОТОКОЛ ДЛЯ ПРЕМЕНОПАУЗЫ (40-50):**
• Магний, омега-3, витамин D
• В дни низкой энергии — только мягкие нагрузки
• В дни подъема — делай важные дела
• Следи за сном (7-8 часов)
"""
        
        # Кнопки
        kb = InlineKeyboardBuilder()
        kb.button(text="📊 График на неделю", callback_data="energy_week_chart")
        kb.button(text="📅 Прогноз на месяц", callback_data="energy_month_text")
        
        if forecast_type == "no_cycle":
            kb.button(text="💖 Забота о себе", callback_data="self_care_no_cycle")
        else:
            kb.button(text="💖 Протокол заботы", callback_data="self_care_protocol")
        
        kb.adjust(2, 1)
        
        await message.answer(urgent_advice + text, reply_markup=kb.as_markup())
        
    except Exception as e:
        print(f"❌ Ошибка в energy_forecast_menu: {e}")
        await message.answer("❌ Временная ошибка. Попробуй позже.")
    

@menu_router.message(F.text == "🎉 КОД СВОБОДА")
async def cheat_menu(message: types.Message):
    """Код Свобода (чит-мил)"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="🎉 Сегодня", callback_data="cheat_today")
    kb.button(text="📅 Завтра", callback_data="cheat_tomorrow")
    kb.button(text="❌ Отмена", callback_data="cheat_cancel")
    kb.adjust(2)
    
    await message.answer(
        "🍕 **Код Свобода**\n\n"
        "Запланируй свой чит-мил:",
        reply_markup=kb.as_markup()
    )


@menu_router.message(F.text == "⚙️ НАСТРОЙКИ")
async def settings_menu(message: types.Message):
    """Настройки профиля"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⏰ Время пробуждения", callback_data="settings_wake")
    kb.button(text="🌍 Часовой пояс", callback_data="settings_tz")
    kb.button(text="📏 Параметры тела", callback_data="settings_body")
    kb.button(text="🔄 Сбросить цикл", callback_data="settings_cycle")
    kb.button(text="🗑️ Сбросить всё", callback_data="settings_reset")
    kb.adjust(1)
    
    await message.answer(
        "⚙️ **Настройки профиля:**",
        reply_markup=kb.as_markup()
    )

@menu_router.message(F.text == "🔄 АНАЛИЗ РИСКОВ")
async def risk_analysis_handler(message: types.Message):
    """Показать анализ рисков"""
    from cycle_integration import CycleIntegrator
    
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    integrator = CycleIntegrator(user)
    report = integrator.get_daily_risk_report()
    
    await message.answer(report)

@menu_router.message(F.text == "💳 ПОДПИСКА")
async def subscription_menu(message: types.Message):
    """Меню подписки"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    # Проверяем текущий статус
    status = user.get('subscription_status', 'free')
    until = user.get('subscription_until', 'не указано')
    
    status_text = {
        'free': '🆓 Бесплатный',
        'core': '⭐ CORE',
        'vip': '💎 VIP'
    }
    
    text = f"**Твой тариф:** {status_text.get(status, '🆓 Бесплатный')}\n"
    if status != 'free':
        text += f"📅 Действует до: {until}\n\n"
    else:
        text += "\n"
    
    text += "**Доступные тарифы:**\n"
    text += "⭐ CORE — 1490₽/мес\n"
    text += "💎 VIP — 3990₽/мес\n"
    text += "📅 Годовые со скидкой 37-45%\n\n"
    text += "**Что входит:**\n"
    text += "• CORE: все базовые протоколы\n"
    text += "• VIP: + генетика, психолог, расширенные анализы"
    
    kb = InlineKeyboardBuilder()
    kb.button(text="⭐ Купить CORE", callback_data="buy_core")
    kb.button(text="💎 Купить VIP", callback_data="buy_vip")
    kb.button(text="📅 CORE год", callback_data="buy_core_year")
    kb.button(text="📅 VIP год", callback_data="buy_vip_year")
    kb.adjust(2)
    
    await message.answer(text, reply_markup=kb.as_markup())


# ==================== CALLBACK ОБРАБОТЧИКИ ====================

@menu_router.callback_query(F.data == "wake_up")
async def wake_up_callback(callback: types.CallbackQuery, state: FSMContext):
    """Начать утренний опрос"""
    # Импортируем здесь, чтобы избежать циклических импортов
    try:
        from bot import Morning
        await callback.message.delete()
        await callback.message.answer(
            BotTexts.WAKE_UP_PROMPT.format(name=(get_user(callback.from_user.id) or {}).get('power_name', '')),
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(Morning.sleep_quality)
    except Exception as e:
        print(f"Ошибка в wake_up_callback: {e}")
        await callback.message.answer("❌ Ошибка. Попробуй позже.")
    await callback.answer()


@menu_router.callback_query(F.data == "cns_today")
async def cns_today_callback(callback: types.CallbackQuery):
    """Показать день ЦНС"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    today = date.today()
    rhythm_start = date.fromisoformat(user['rhythm_start'])
    cns_day = (today - rhythm_start).days % 9 + 1
    cns_data = get_cns_phase(cns_day)
    
    text = f"🧠 **День ЦНС {cns_day} — {cns_data['name']}**\n\n"
    text += f"{cns_data['desc']}\n\n"
    text += f"💪 **Рекомендация:** {cns_data['load']}"
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "cycle_today")
async def cycle_today_callback(callback: types.CallbackQuery):
    """Показать день цикла"""
    user = get_user(callback.from_user.id)
    if not user or user['gender_type'] != 1:
        await callback.answer("❌ Нет данных о цикле")
        return
    
    today = date.today()
    cycle_start = date.fromisoformat(user['cycle_start'])
    cycle_length = user.get('cycle_length', 28)
    female_day = (today - cycle_start).days % cycle_length + 1
    female_data = get_female_phase(female_day, cycle_length)
    
    text = f"🩸 **День цикла {female_day} — {female_data['name']}**\n\n"
    text += f"{female_data['description']}\n\n"
    
    if 'nutrition' in female_data:
        text += f"🥗 **Питание:** {female_data['nutrition']}\n"
    if 'hormones' in female_data:
        text += f"🧪 **Гормоны:** {female_data['hormones']}"
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "hiit_today")
async def hiit_today_callback(callback: types.CallbackQuery):
    """Показать HIIT рекомендацию с учетом ЦНС, цикла и луны"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    from datetime import date
    from rhythm_core import get_hiit_recommendation, get_cns_phase, get_female_phase
    from lunar import LunarScience
    
    today = date.today()
    
    # ===== 1. Получаем день ЦНС =====
    rhythm_start = date.fromisoformat(user['rhythm_start'])
    cns_day = (today - rhythm_start).days % 9 + 1
    cns_data = get_cns_phase(cns_day)
    
    # ===== 2. Получаем фазу луны =====
    lunar = LunarScience()
    phase_data = lunar.get_phase()
    p = phase_data['phase']
    
    # Определяем критичность луны
    is_full_moon = abs(p - 0.5) < 0.1  # полнолуние
    is_new_moon = p < 0.03 or p > 0.97  # новолуние
    lunar_risk = is_full_moon or is_new_moon
    
    lunar_status = "🌕 ПОЛНОЛУНИЕ" if is_full_moon else "🌑 НОВОЛУНИЕ" if is_new_moon else "🌙 ОБЫЧНАЯ ФАЗА"
    
    # ===== 3. Собираем все факторы риска =====
    risk_factors = []
    
    # Проверка ЦНС
    if cns_day == 9:
        risk_factors.append("🧠 День ЦНС 9 (Тишина) — полный отдых")
    
    # Проверка луны
    if lunar_risk:
        risk_factors.append(f"🌕 {lunar_status} — повышена свертываемость крови")
    
    # Проверка женского цикла
    if user.get('gender_type') == 1:
        cycle_start = date.fromisoformat(user['cycle_start'])
        cycle_length = user.get('cycle_length', 28)
        female_day = (today - cycle_start).days % cycle_length + 1
        female_data = get_female_phase(female_day, cycle_length)
        
        if 1 <= female_day <= 5:
            risk_factors.append(f"🩸 Менструация (день {female_day})")
        elif 25 <= female_day <= 28:
            risk_factors.append(f"🍂 ПМС (день {female_day})")
    
    # ===== 4. Определяем итоговый вердикт =====
    if risk_factors:
        # Есть факторы риска
        if lunar_risk and cns_day == 9:
            verdict = "🔴 **КРИТИЧЕСКИЙ ЗАПРЕТ**"
            recommendation = "Категорически запрещен любой HIIT. Только покой."
        elif len(risk_factors) >= 2:
            verdict = "🟠 **ВЫСОКИЙ РИСК**"
            recommendation = "HIIT не рекомендуется. Легкая растяжка."
        else:
            verdict = "🟡 **ПОВЫШЕННАЯ ОСТОРОЖНОСТЬ**"
            recommendation = "Легкая активность, йога, прогулка."
        
        # Формируем текст с предупреждением
        text = f"🧘 **HIIT ПРОТОКОЛ**\n\n"
        text += f"📅 **ЦНС:** День {cns_day} — {cns_data['name']}\n"
        text += f"🌙 **Луна:** {lunar_status}\n"
        
        if user.get('gender_type') == 1:
            text += f"🩸 **Цикл:** {female_data['name']} (день {female_day})\n"
        
        text += f"\n{verdict}\n\n"
        text += f"⚠️ **Факторы риска:**\n"
        for factor in risk_factors:
            text += f"• {factor}\n"
        
        text += f"\n💡 **Рекомендация:**\n{recommendation}\n\n"
        
        if lunar_risk:
            text += f"🩸 *В полнолуние/новолуние повышена свертываемость крови. HIIT увеличивает риск тромбоза.*"
        
        await callback.message.edit_text(text)
        await callback.answer()
        return
    
    # ===== 5. Если всё ок — показываем обычный протокол =====
    recommendation = get_hiit_recommendation(user)
    
    text = f"{recommendation}\n\n"
    text += f"🧠 **ЦНС:** День {cns_day} — {cns_data['name']}\n"
    text += f"🌙 **Луна:** {lunar_status}"
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "supplements_today")
async def supplements_today_callback(callback: types.CallbackQuery):
    """Показать рекомендации по БАДам с предупреждениями"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    today = date.today()
    rhythm_start = date.fromisoformat(user['rhythm_start'])
    cns_day = (today - rhythm_start).days % 9 + 1
    
    # ===== БАЗОВЫЕ РЕКОМЕНДАЦИИ =====
    text = "💊 **БАДы на сегодня:**\n\n"
    
    # УТРО
    text += "🌅 **УТРО (с завтраком):**\n"
    text += "• Витамин D3 2000-5000 МЕ (с жирами)\n"
    text += "• Омега-3 1-2 г (EPA/DHA)\n"
    text += "• Магний (только если не на ночь)\n"
    
    # ДЕНЬ
    text += "\n🌞 **ДЕНЬ (после еды):**\n"
    text += "• Комплекс В\n"
    text += "• Цинк 15-30 мг\n"
    
    # ВЕЧЕР
    text += "\n🌙 **ВЕЧЕР (перед сном):**\n"
    text += "• Магний (глицинат/треонат) 300-500 мг\n"
    text += "• Мелатонин 1-3 мг (при необходимости)\n"
    
    # ===== ДОПОЛНЕНИЯ ПО ЦИКЛУ =====
    if user.get('gender_type') == 1:
        cycle_start = date.fromisoformat(user['cycle_start'])
        cycle_length = user.get('cycle_length', 28)
        female_day = (today - cycle_start).days % cycle_length + 1
        
        text += "\n🩸 **ПО ФАЗЕ ЦИКЛА:**\n"
        if 1 <= female_day <= 5:
            text += "• + Железо (только при подтвержденном дефиците!)\n"
        elif 10 <= female_day <= 15:
            text += "• + Фолаты (400-800 мкг)\n"
        elif 16 <= female_day <= 22:
            text += "• + Магний 400-600 мг\n"
    
    # ===== ДОПОЛНЕНИЯ ПО ЦНС =====
    if cns_day == 9:
        text += "\n🧠 **ДЕНЬ ТИШИНЫ (ЦНС 9):**\n"
        text += "• Снизь стимуляторы (кофеин, энергетики)\n"
        text += "• Увеличь магний на 100-200 мг\n"
    
    # ===== ⚠️ ПРЕДУПРЕЖДЕНИЯ ПО БАДАМ =====
    text += "\n" + "="*40 + "\n"
    text += "⚠️ **ВАЖНЫЕ ПРЕДУПРЕЖДЕНИЯ:**\n\n"
    
    text += "💊 **Витамин D3:**\n"
    text += "• Перед приемом сдай анализ 25(OH)D\n"
    text += "• Дозировка зависит от уровня дефицита\n"
    text += "• Принимать с жирами для усвоения\n\n"
    
    text += "💊 **Железо:**\n"
    text += "• Принимать ТОЛЬКО при подтвержденном дефиците (ферритин < 40)\n"
    text += "• Не сочетать с кальцием, кофе, чаем\n"
    text += "• Передозировка опасна для печени\n\n"
    
    text += "💊 **Магний:**\n"
    text += "• В высоких дозах (более 600 мг) может вызвать диарею\n"
    text += "• Глицинат — для сна, треонат — для мозга\n"
    text += "• Не сочетать с антибиотиками (интервал 2-3 часа)\n\n"
    
    text += "💊 **Цинк:**\n"
    text += "• Более 40 мг/день вызывает дефицит меди\n"
    text += "• Принимать с едой, чтобы избежать тошноты\n\n"
    
    text += "💊 **Омега-3:**\n"
    text += "• Разжижает кровь (осторожно с антикоагулянтами!)\n"
    text += "• Хранить в холодильнике, чтобы не прогоркла\n\n"
    
    text += "💊 **Мелатонин:**\n"
    text += "• Начинать с 1 мг, не превышать 3 мг\n"
    text += "• Не принимать при аутоиммунных заболеваниях\n"
    text += "• Не смешивать с алкоголем\n\n"
    
    text += "💊 **Общие правила:**\n"
    text += "• Вводить БАДы по одному (3-5 дней между новыми)\n"
    text += "• При появлении сыпи, зуда, тошноты — отменить\n"
    text += "• Делать перерывы в приеме (1-2 месяца работы, 1 месяц отдыха)\n\n"
    
    text += "❗ **Главное:**\n"
    text += "БАДы — это не лекарства. Они не лечат болезни, а восполняют дефициты.\n"
    text += "Никакие добавки не заменят сон, питание и движение.\n\n"
    
    text += "⚠️ ** Все дозировки указаны как рекомендованные на основе научных исследований . Эффективность и безопасность зависят от индивидуальных особенностей. Перед началом приема обязательно проконсультируйтесь с врачом и сдайте анализы для выявления дефицитов. БАДы не являются лекарственными средствами.**"
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "genetics_quick")
async def genetics_quick_callback(callback: types.CallbackQuery):
    """Быстрый просмотр генетики"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    if not has_access(callback.from_user.id, 'vip'):
        kb = InlineKeyboardBuilder()
        kb.button(text="💳 Купить VIP", callback_data="buy_vip")
        await callback.message.edit_text(
            "🧬 Генетический модуль доступен только в VIP",
            reply_markup=kb.as_markup()
        )
        await callback.answer()
        return
    
    if not user.get('genetics_mthfr'):
        kb = InlineKeyboardBuilder()
        kb.button(text="📤 Загрузить данные", callback_data="genetics_file")
        kb.button(text="✏️ Ввести вручную", callback_data="genetics_manual")
        await callback.message.edit_text(
            "🧬 **Нет генетических данных**\n\n"
            "Загрузи файл или введи вручную:",
            reply_markup=kb.as_markup()
        )
        await callback.answer()
        return
    
    try:
        from bot import generate_genetics_report
        result = generate_genetics_report(
            user.get('genetics_mthfr', ''),
            user.get('genetics_fto', ''),
            user.get('genetics_actn3', '')
        )
        await callback.message.edit_text(result)
    except:
        # Упрощенный вариант, если не удалось импортировать
        text = "🧬 **Твои генетические данные:**\n\n"
        text += f"MTHFR: {user.get('genetics_mthfr', 'не указано')}\n"
        text += f"FTO: {user.get('genetics_fto', 'не указано')}\n"
        text += f"ACTN3: {user.get('genetics_actn3', 'не указано')}\n\n"
        text += "Подробный отчет скоро будет доступен."
        await callback.message.edit_text(text)
    
    await callback.answer()

# ==================== ЛУННЫЙ КАЛЕНДАРЬ ====================

@menu_router.callback_query(F.data == "lunar_info")
async def lunar_info_callback(callback: types.CallbackQuery):
    """Показать лунный календарь"""
    from lunar import LunarScience, format_lunar_report
    
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди регистрацию", show_alert=True)
        return
    
    lunar = LunarScience()
    data = lunar.get_full_recommendation()
    report = format_lunar_report(data)
    
    await callback.message.edit_text(report)
    await callback.answer()

@menu_router.callback_query(F.data == "nutrition_breakfast")
async def nutrition_breakfast_callback(callback: types.CallbackQuery):
    """Рекомендации по завтраку"""
    text = """🍳 **ЗАВТРАК**

**Время:** через 1.5 часа после пробуждения

**Основа:** Белки + Жиры

**Варианты:**
• Омлет с авокадо
• Рыба с овощами
• Яйца пашот с зеленью

**БАДы:**
• D3 2000-5000 МЕ
• Омега-3 2г

❌ **Исключить:**
• Каши, хлопья
• Сладкое
• Фрукты (после еды)

💡 **Принцип:** стабильный сахар = стабильная энергия"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "nutrition_lunch")
async def nutrition_lunch_callback(callback: types.CallbackQuery):
    """Рекомендации по обеду"""
    text = """🥗 **ОБЕД**

**Время:** 13:00

**Основа:** Белок + Сложные углеводы + Клетчатка

**Варианты:**
• Гречка с курицей и овощами
• Киноа с рыбой и зеленью
• Чечевица с индейкой

**Порядок приема:**
1. 🥗 Клетчатка (салат)
2. 🍖 Белок
3. 🍚 Углеводы

💡 **Принцип:** самый плотный прием пищи"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "nutrition_dinner")
async def nutrition_dinner_callback(callback: types.CallbackQuery):
    """Рекомендации по ужину"""
    text = """🌱 **УЖИН**

**Время:** 18:00

**Основа:** Только растительная пища

**Варианты:**
• Тушеные овощи
• Салат с авокадо
• Овощной суп

**БАДы:**
• Магний (глицинат/треонат)

❌ **Исключить:**
• Животный белок
• Тяжелую пищу
• Углеводы

💡 **Принцип:** дать организму отдохнуть"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "mindful_eating")
async def mindful_eating_callback(callback: types.CallbackQuery, state: FSMContext):
    """Запуск осознанного питания из инлайн-меню"""
    print(f"📌 Callback ID: {callback.from_user.id}")
    
    # 👇 ЯВНО ПЕРЕДАЁМ user_id
    user_id = callback.from_user.id
    
    # Проверяем пользователя прямо здесь
    user = get_user(user_id)
    if not user:
        print(f"❌ Пользователь {user_id} НЕ найден в БД")
        await callback.answer("Сначала пройди регистрацию", show_alert=True)
        return
    
    from mindful_eating import start_mindful_eating
    
    await callback.message.delete()
    # 👇 ПЕРЕДАЁМ user_id отдельно
    await start_mindful_eating(user_id, callback.message, state)
    await callback.answer()

@menu_router.callback_query(F.data == "energy_month_text")
async def energy_month_text_callback(callback: types.CallbackQuery):
    """Показать текстовый прогноз на месяц"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return
    
    from energy_forecast import EnergyForecast
    
    await callback.message.answer("📅 Генерирую прогноз на месяц... Это может занять несколько секунд.")
    
    try:
        forecast = EnergyForecast(user)
        month = forecast.get_month_forecast()
        
        if not month:
            await callback.message.answer("❌ Ошибка при расчете прогноза")
            await callback.answer()
            return
        
        # Разбиваем на недели для удобства чтения
        text = "📅 **ПРОГНОЗ ЭНЕРГИИ НА МЕСЯЦ**\n\n"
        
        for i in range(0, len(month), 7):
            week = month[i:i+7]
            text += f"**Неделя {i//7 + 1}**\n"
            for day in week:
                emoji = "🔴" if day['energy'] >= 80 else "🟡" if day['energy'] >= 60 else "🟢" if day['energy'] >= 40 else "🔵"
                text += f"{emoji} {day['date'].strftime('%d.%m')}: {day['energy']}%\n"
            text += "\n"
        
        text += "🔴 Высокая | 🟡 Средняя | 🟢 Нормальная | 🔵 Низкая"
        
        # Разбиваем длинные сообщения (Telegram лимит 4096 символов)
        if len(text) > 3500:
            parts = [text[i:i+3500] for i in range(0, len(text), 3500)]
            for part in parts:
                await callback.message.answer(part)
        else:
            await callback.message.answer(text)
            
    except Exception as e:
        print(f"❌ Ошибка в energy_month_text_callback: {e}")
        await callback.message.answer("❌ Ошибка при расчете прогноза")
    
    await callback.answer()


@menu_router.callback_query(F.data == "my_recipes")
async def my_recipes_callback(callback: types.CallbackQuery):
    """Показать рецепты"""
    text = """📋 **МОИ РЕЦЕПТЫ**

**Завтраки:**
• Омлет с авокадо
• Яйца пашот с зеленью

**Обеды:**
• Гречка с курицей
• Рыба с киноа

**Ужины:**
• Овощное рагу
• Салат с авокадо

**Перекусы:**
• Орехи (30г)
• Овощные палочки

💡 **Скоро:** персональная база рецептов"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "stats_morning")
async def stats_morning_callback(callback: types.CallbackQuery):
    """Показать утреннюю статистику"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT date, sleep_quality, pulse_delta 
            FROM morning_checkin 
            WHERE user_id = ? 
            ORDER BY date DESC LIMIT 7
        """, (callback.from_user.id,))
        mornings = cur.fetchall()
    
    if not mornings:
        await callback.message.edit_text("📊 Нет данных утренних замеров")
        await callback.answer()
        return
    
    text = f"📈 **Утренние замеры для {user['power_name']}**\n\n"
    for m in mornings:
        sleep_emoji = "🟢" if m[1] >= 4 else "🟡" if m[1] >= 3 else "🔴"
        pulse_emoji = "✅" if m[2] <= 15 else "⚠️" if m[2] <= 20 else "🔴"
        text += f"📅 {m[0]}: {sleep_emoji} Сон {m[1]}/5, {pulse_emoji} Пульс {m[2]} дельта\n"
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "stats_evening")
async def stats_evening_callback(callback: types.CallbackQuery):
    """Показать вечернюю статистику"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT date, nutrition_timing, nutrition_mindful, hiit_done, motivation, energy, emotional
            FROM evening_audit 
            WHERE user_id = ? 
            ORDER BY date DESC LIMIT 7
        """, (callback.from_user.id,))
        evenings = cur.fetchall()
    
    if not evenings:
        await callback.message.edit_text("📊 Нет данных вечерних аудитов")
        await callback.answer()
        return
    
    text = f"🌙 **Вечерние аудиты для {user['power_name']}**\n\n"
    for e in evenings:
        avg = (e[1] + e[2] + e[4] + e[5] + e[6]) / 5
        hiit = "✅" if e[3] else "❌"
        text += f"📅 {e[0]}: {hiit} HIIT, средний {avg:.1f}/5\n"
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "stats_weekly")
async def stats_weekly_callback(callback: types.CallbackQuery):
    """Показать недельные замеры"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("""
            SELECT date, weight, waist, hips, chest
            FROM weekly_metrics 
            WHERE user_id = ? 
            ORDER BY date DESC LIMIT 4
        """, (callback.from_user.id,))
        weekly = cur.fetchall()
    
    if not weekly:
        await callback.message.edit_text("📊 Нет данных недельных замеров")
        await callback.answer()
        return
    
    text = f"📏 **Недельные замеры для {user['power_name']}**\n\n"
    for w in weekly:
        text += f"📅 {w[0]}:\n"
        text += f"   ⚖️ Вес: {w[1]} кг\n"
        text += f"   📐 Талия: {w[2]} см\n"
        if w[3]:
            text += f"   📏 Бедра: {w[3]} см\n"
        if w[4]:
            text += f"   📐 Грудь: {w[4]} см\n"
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "achievements")
async def achievements_callback(callback: types.CallbackQuery):
    """Показать достижения"""
    from gamification import ACHIEVEMENTS
    
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
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
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "my_points")
async def my_points_callback(callback: types.CallbackQuery):
    """Показать информацию об очках"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("❌ Пользователь не найден")
        return
    
    points = user.get('bio_points', 0)
    gender = user.get('gender_type', 1)
    
    # Используем класс GamificationSystem для получения звания
    from gamification import GamificationSystem
    import sqlite3
    
    # Создаем временный объект gamification
    gamification = GamificationSystem(sqlite3.connect('users.db'))
    title = gamification.get_title(points, gender)
    
    text = f"⭐ **МОИ ОЧКИ**\n\n"
    text += f"Всего: **{points}** ⭐\n"
    text += f"Текущий уровень: {title['emoji']} **{title['name']}**\n"
    text += f"{title['desc']}\n\n"
    
    # Информация о следующем уровне
    if gender == 1:
        titles = FEMALE_TITLES
    else:
        titles = MALE_TITLES
    
    next_title = None
    for i, t in enumerate(titles):
        if t['min'] <= points <= t['max'] and i < len(titles) - 1:
            next_title = titles[i + 1]
            break
    
    if next_title:
        need = next_title['min'] - points
        text += f"🎯 До следующего уровня: **{need}** ⭐\n"
        text += f"{next_title['emoji']} {next_title['name']}\n\n"
    
    text += "\n**Как получать очки:**\n"
    text += "• Утренний опрос: +10 ⭐\n"
    text += "• Вечерний аудит: +15 ⭐\n"
    text += "• HIIT: +20 ⭐\n"
    text += "• Вода: +1 ⭐\n"
    text += "• Серия дней: +50 ⭐"
    
    await callback.message.edit_text(text)
    await callback.answer()

@menu_router.callback_query(F.data == "self_care_protocol")
async def self_care_protocol_callback(callback: types.CallbackQuery):
    """Протокол заботы о себе"""
    text = """
💖 **ПРОТОКОЛ ЗАБОТЫ О СЕБЕ**

🌟 **В ДНИ НИЗКОЙ ЭНЕРГИИ (0-40%):**

🌅 **УТРО:**
• Не вскакивай — полежи 5-10 мин
• «Тараканчик» в постели (тряска руками/ногами)
• Теплая вода с лимоном, псиллиумом, щепоткой морской соли

🍲 **ДЕНЬ:**
• Только теплая еда (супы-пюре, тушеные овощи)
• Костный бульон — твой эликсир
• Никаких сырых овощей и холодных смузи

🌳 **ВЕЧЕР:**
• Прогулка 30 мин без телефона
• Ванна с магниевой солью (500г, 37-38°C)
• Теплый чай с мелиссой

🌙 **НОЧЬ:**
• В 21:00 — режим «Авиа» (никаких экранов)
• Дыхание 4-7-8 (10 циклов)
• Сон 8-9 часов

🌟 **В ДНИ ВЫСОКОЙ ЭНЕРГИИ (80-100%):**

⚡ **ДЕЛАЙ:**
• Тяжелые тренировки
• Важные встречи и решения
• Новые проекты и начинания

🧘 **НЕ ЗАБЫВАЙ:**
• Даже в пик — слушай тело
• Пей больше воды
• Не перегружайся

💫 **ГЛАВНОЕ:**
• Твой цикл — не приговор, а суперсила
• Зная его, ты можешь планировать жизнь
• Отдых так же важен, как и активность
• Ты не ленивая — ты следуешь биологии

*Береги себя. Ты у себя одна. Помни! Ты не ленишься. Ты проводишь сложнейшую биологическую операцию по восстановлению нейрохимии своего тела и мозга.* 💖
"""
    await callback.message.answer(text)
    await callback.answer()



@menu_router.callback_query(F.data == "sos_sugar")
async def sos_sugar_callback(callback: types.CallbackQuery):
    """Помощь при тяге к сладкому"""
    text = """🍬 **ТЯНЕТ НА СЛАДКОЕ**

**Что делать прямо сейчас:**

1. 💧 **Вода**
   Выпей стакан воды с лимоном

2. 🥜 **Белок**
   Съешь горсть орехов или яйцо

3. 🧘 **Пауза**
   5 минут глубокого дыхания

4. 🚶 **Движение**
   Выйди на 10 мин прогуляться

**Почему тянет:**
• Скачок/падение сахара
• Нехватка белка в предыдущем приеме
• Эмоциональный голод

💡 **Превенция:**
Белковый завтрак (30г) = нет тяги днем"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "sos_stress")
async def sos_stress_callback(callback: types.CallbackQuery):
    """Помощь при стрессе/тревоге"""
    text = """😰 **СТРЕСС И ТРЕВОГА**

**Экстренная помощь:**

1. 🌬️ **Дыхание 4-7-8**
   Вдох (4 сек) → Задержка (7 сек) → Выдох (8 сек)
   Повтори 4 раза

2. 🌿 **Магний**
   Прими цитрат/глицинат магния

3. 🧠 **Заземление**
   Найди 5 вещей вокруг, 4 звука, 3 ощущения

4. 🚰 **Вода**
   Медленно выпей стакан теплой воды

**На вечер:**
• Теплая ванна с магниевой солью
• Без гаджетов за час до сна
• Ашваганда (если есть)

💡 **Помни:** стресс блокирует жиросжигание"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "sos_fatigue")
async def sos_fatigue_callback(callback: types.CallbackQuery):
    """Помощь при упадке сил"""
    text = """😴 **УПАДОК СИЛ**

**Что делать:**

1. 💧 **Вода + соль**
   Стакан воды с щепоткой соли

2. ☀️ **Свет**
   Выйди на солнце/яркий свет на 10 мин

3. 🚶 **Движение**
   Быстрая ходьба или прыжки 5 мин

4. 🧠 **Контраст**
   Умой лицо холодной водой

**Проверь:**
• Достаточно ли белка сегодня?
• Было ли солнце?
• Не перетренировался ли вчера?

**Запрещено:**
❌ Кофе (если не спал ночью)
❌ Сладкое (временный подъем → крах)
❌ Лечь спать днем (собьет режим)"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "sos_binge")
async def sos_binge_callback(callback: types.CallbackQuery):
    """Помощь при срыве/переедании"""
    text = """🍽️ **СРЫВ / ПЕРЕЕДАНИЕ**

**Стоп-кран:**

1. 🛑 **СТОП**
   Прекрати есть прямо сейчас

2. 💧 **Вода**
   Медленно выпей 2 стакана воды

3. 🚶 **Уйти**
   Смени обстановку, выйди на улицу

4. 🧘 **Без самобичевания**
   Один срыв не отменяет прогресса

**Что дальше:**
• Следующий прием - по расписанию
• Без пропусков и жестких диет
• Белок в каждый прием

💡 **Анализ:**
Что триггернуло? Голод? Эмоции? Усталость?

✅ **Код Свобода:** если это был запланированный чит-мил, наслаждайся без чувства вины!"""
    
    await callback.message.edit_text(text)
    await callback.answer()


@menu_router.callback_query(F.data == "settings_wake")
async def settings_wake_callback(callback: types.CallbackQuery, state: FSMContext):
    """Изменить время пробуждения"""
    try:
        from bot import Reg
        await callback.message.delete()
        await callback.message.answer(
            "⏰ **Введи новое время пробуждения**\n\n"
            "Формат: ЧЧ.ММ (например, 07.30)",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(Reg.wake_time)
    except Exception as e:
        print(f"Ошибка в settings_wake_callback: {e}")
        await callback.message.answer("❌ Ошибка. Попробуй позже.")
    await callback.answer()


@menu_router.callback_query(F.data == "settings_tz")
async def settings_tz_callback(callback: types.CallbackQuery, state: FSMContext):
    """Изменить часовой пояс"""
    try:
        from bot import Reg
        kb = ReplyKeyboardBuilder()
        for opt in BotTexts.TZ_OPTIONS:
            kb.button(text=opt)
        
        await callback.message.delete()
        await callback.message.answer(
            "🌍 **Выбери свой часовой пояс:**",
            reply_markup=kb.adjust(1).as_markup(resize_keyboard=True)
        )
        await state.set_state(Reg.tz)
    except Exception as e:
        print(f"Ошибка в settings_tz_callback: {e}")
        await callback.message.answer("❌ Ошибка. Попробуй позже.")
    await callback.answer()


@menu_router.callback_query(F.data == "settings_body")
async def settings_body_callback(callback: types.CallbackQuery, state: FSMContext):
    """Изменить параметры тела"""
    try:
        from bot import Reg
        await callback.message.delete()
        await callback.message.answer(
            "📏 **Введи новые параметры**\n\n"
            "В одной строке через пробел:\n"
            "Вес Талия Бедра\n"
            "Например: 65 70 95",
            reply_markup=types.ReplyKeyboardRemove()
        )
        await state.set_state(Reg.body_params)
    except Exception as e:
        print(f"Ошибка в settings_body_callback: {e}")
        await callback.message.answer("❌ Ошибка. Попробуй позже.")
    await callback.answer()


@menu_router.callback_query(F.data == "settings_cycle")
async def settings_cycle_callback(callback: types.CallbackQuery):
    """Сбросить цикл"""
    user = get_user(callback.from_user.id)
    if not user or user['gender_type'] != 1:
        await callback.answer("❌ Функция только для женщин с циклом")
        return
    
    today = date.today()
    new_cycle_start = today.isoformat()
    new_rhythm_start = (today + timedelta(days=5)).isoformat()
    
    update_user_db(callback.from_user.id, {
        'cycle_start': new_cycle_start,
        'rhythm_start': new_rhythm_start
    })
    
    await callback.message.edit_text(
        "✅ **Цикл сброшен!**\n\n"
        "Новый цикл начат сегодня.\n"
        "Ритм ЦНС перестроен."
    )
    await callback.answer()


@menu_router.callback_query(F.data == "settings_reset")
async def settings_reset_callback(callback: types.CallbackQuery):
    """Сбросить все данные"""
    kb = InlineKeyboardBuilder()
    kb.button(text="✅ ДА, СБРОСИТЬ ВСЁ", callback_data="confirm_reset")
    kb.button(text="❌ ОТМЕНА", callback_data="cancel_reset")
    
    await callback.message.edit_text(
        "⚠️ **ВНИМАНИЕ!**\n\n"
        "Ты собираешься удалить ВСЕ свои данные:\n"
        "• Профиль\n"
        "• Замеры\n"
        "• Аудиты\n"
        "• Прогресс\n\n"
        "Это действие необратимо.\n\n"
        "**Точно сбросить всё?**",
        reply_markup=kb.as_markup()
    )
    await callback.answer()


@menu_router.callback_query(F.data == "confirm_reset")
async def confirm_reset_callback(callback: types.CallbackQuery):
    """Подтверждение сброса"""
    with sqlite3.connect('users.db') as conn:
        cur = conn.cursor()
        cur.execute("DELETE FROM users WHERE user_id = ?", (callback.from_user.id,))
        cur.execute("DELETE FROM morning_checkin WHERE user_id = ?", (callback.from_user.id,))
        cur.execute("DELETE FROM evening_audit WHERE user_id = ?", (callback.from_user.id,))
        cur.execute("DELETE FROM weekly_metrics WHERE user_id = ?", (callback.from_user.id,))
        cur.execute("DELETE FROM water_logs WHERE user_id = ?", (callback.from_user.id,))
        conn.commit()
    
    await callback.message.edit_text(
        "🔄 **Все данные удалены.**\n\n"
        "Для новой регистрации отправь /start"
    )
    await callback.answer()

@water_router.callback_query(F.data == "water_log")
async def water_log_callback(callback: types.CallbackQuery):
    """Отметить выпитый стакан"""
    from utils import get_user, update_user_db
    from bot import award_points
    
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди регистрацию", show_alert=True)
        return
    
    consumed = user.get('water_consumed_today', 0)
    goal = user.get('water_goal', 2000)
    
    new_consumed = consumed + 250
    if new_consumed > goal:
        new_consumed = goal
    
    update_user_db(callback.from_user.id, {'water_consumed_today': new_consumed})
    await award_points(callback.from_user.id, "water_glass", callback.message)
    
    await callback.answer(f"✅ +250 мл! Прогресс: {new_consumed}/{goal} мл")
    
    # Обновляем сообщение
    from water_calculator import WaterCalculator
    user = get_user(callback.from_user.id)
    user['water_consumed_today'] = new_consumed
    user['water_goal'] = goal
    report = WaterCalculator.format_report(user)
    
    await callback.message.edit_text(report)

@water_router.callback_query(F.data == "water_schedule")
async def water_schedule_callback(callback: types.CallbackQuery):
    """Показать расписание"""
    from utils import get_user
    import json
    from water_calculator import WaterCalculator
    
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Сначала пройди регистрацию", show_alert=True)
        return
    
    total = user.get('water_goal', 2000)
    water_plan = json.loads(user.get('water_preferences', '{}'))
    
    if not water_plan or 'schedule' not in water_plan:
        schedule = WaterCalculator.get_schedule(total)
    else:
        schedule = water_plan.get('schedule', [])
    
    text = "⏰ **ПОЛНОЕ РАСПИСАНИЕ ВОДЫ:**\n\n"
    for item in schedule:
        text += f"**{item['time']}** — {item['name']}\n"
        text += f"📏 {item['ml']} мл • {item['type']}\n"
        text += f"🧹 {item['motilin']}\n\n"
    
    await callback.message.answer(text)
    await callback.answer()

@water_router.callback_query(F.data == "water_motilin")
async def water_motilin_callback(callback: types.CallbackQuery):
    """Информация о мотилине"""
    text = """
🧹 **ПИЩЕВАЯ ДОМОХОЗЯЙКА (МОТИЛИН)**

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

🔬 *Исследования: Sanger, G. J., et al. (2016)*
"""
    await callback.message.answer(text)
    await callback.answer()

@water_router.callback_query(F.data == "water_explain")
async def water_explain_callback(callback: types.CallbackQuery):
    """Объяснение расчета воды"""
    text = """
🧠 **КАК РАССЧИТЫВАЕТСЯ ВОДА**

📊 **Формула:** вес × 30 мл (база)

➕ **Добавки:**
• Активность: +10 мл на минуту тренировки
• Белок: +7 мл на грамм белка
• Генетика FTO: +10% для AA/AT (риск обезвоживания)
• Лютеиновая фаза: +10% (задержка воды)
• Жара: +20%

⚠️ **Важно:**
• Учитывается жидкость из еды (~700 мл/день)
• Кофе и алкоголь требуют доп. воды
• При болезнях почек/сердца — консультация врача

💡 **Правила:**
• Пить равномерно в течение дня
• Не залпом
• Слушать жажду
"""
    await callback.message.answer(text)
    await callback.answer()


@menu_router.callback_query(F.data == "energy_week_chart")
async def energy_week_chart_callback(callback: types.CallbackQuery):
    """Показать график энергии на неделю"""
    user = get_user(callback.from_user.id)
    if not user:
        await callback.answer("Пользователь не найден")
        return
    
    from energy_forecast import EnergyForecast
    
    try:
        forecast = EnergyForecast(user)
        buf = forecast.plot_week_energy()
        
        if buf:
            await callback.message.answer_photo(
                types.BufferedInputFile(buf.getvalue(), filename="energy_week.png"),
                caption="📊 **Прогноз энергии на неделю**"
            )
        else:
            await callback.message.answer("❌ Не удалось создать график")
            
    except Exception as e:
        print(f"❌ Ошибка в energy_week_chart_callback: {e}")
        await callback.message.answer("❌ Ошибка при создании графика")
    
    await callback.answer()

@menu_router.callback_query(F.data == "self_care_no_cycle")
async def self_care_no_cycle_callback(callback: types.CallbackQuery):
    """Протокол заботы для женщин без цикла"""
    user = get_user(callback.from_user.id)
    age = user.get('age', 45) if user else 45
    
    if age >= 50:
        text = """
🌙 **ПРОТОКОЛ ЗАБОТЫ: МЕНОПАУЗА (50+)**

💊 **БАДЫ:**
• Омега-3 — 2-3 г/день (противовоспалительное)
• Витамин D3 — 2000-5000 МЕ (с анализами)
• Магний глицинат — 400 мг на ночь
• Кальций + K2 — для костей

🥗 **ПИТАНИЕ:**
• Костный бульон ежедневно (коллаген)
• Жирная рыба 2-3 раза в неделю
• Овощи, зелень, авокадо
• Исключить сахар и быстрые углеводы

🏃‍♀️ **ТРЕНИРОВКИ:**
• Силовые 2-3 раза в неделю (кости!)
• Прогулки 30-40 мин ежедневно
• Йога, растяжка
• HIIT — заменить на интервалы низкой интенсивности

🧘 **ОБРАЗ ЖИЗНИ:**
• Сон 7-8 часов (ложиться до 23:00)
• Управление стрессом (дыхание, медитация)
• Контрастный душ
• Прогулки на солнце

💫 *Твое тело меняется — это нормально. 
  Главное — поддерживать его с заботой.*
"""
    else:
        text = """
🌸 **ПРОТОКОЛ ЗАБОТЫ: ПРЕМЕНОПАУЗА (40-50)**

📊 **СЛУШАЙ СВОЕ ТЕЛО:**
• Энергия может скакать — это нормально
• Веди дневник самочувствия
• Отмечай дни подъема и спада

💊 **БАДЫ:**
• Магний — 400 мг на ночь
• Омега-3 — 1-2 г/день
• Витамин D3 — 2000-4000 МЕ
• Витамины группы В

🥗 **ПИТАНИЕ:**
• Белок в каждый прием (яйца, рыба, мясо)
• Сложные углеводы до 15:00
• Много овощей и зелени
• Ограничить кофеин

🏃‍♀️ **ТРЕНИРОВКИ:**
• В дни высокой энергии — силовые, HIIT
• В дни низкой энергии — прогулки, йога
• Плавание — идеально для всех дней

💖 *Ты входишь в новый этап. 
  Познай свое тело заново.*
"""
    
    await callback.message.answer(text)
    await callback.answer()

@menu_router.callback_query(F.data == "cancel_reset")
async def cancel_reset_callback(callback: types.CallbackQuery):
    """Отмена сброса"""
    await callback.message.edit_text("✅ Отмена. Твои данные в безопасности.")
    await callback.answer()


print("✅ Все хэндлеры зарегистрированы")
print("🔥🔥🔥 menu.py ЗАГРУЗКА ЗАВЕРШЕНА 🔥🔥🔥")

@menu_router.message(F.text == "👤 МОЙ ПРОФИЛЬ")
async def profile_menu(message: types.Message):
    """Показать профиль"""
    user = get_user(message.from_user.id)
    if not user:
        return await message.answer("Сначала пройди регистрацию: /start")
    
    # Показываем профиль из gamification
    await show_profile(message)


# ==================== ЭКСПОРТ ====================
__all__ = ['menu_router', 'show_main_menu']
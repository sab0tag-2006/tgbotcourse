# water_calculator.py
import json
import datetime
from typing import Dict, Any, List
from aiogram import Router, types, F
from aiogram.utils.keyboard import InlineKeyboardBuilder

water_router = Router()


class WaterCalculator:
    """
    Точный расчет воды с учетом всех факторов:
    - Вес, активность, климат
    - Генетика FTO
    - Фаза цикла
    - Белковая нагрузка
    """
    
    @staticmethod
    def calculate_base(user_weight: float) -> int:
        """Базовая норма: 30 мл на кг"""
        return int(user_weight * 30)
    
    @staticmethod
    def activity_correction(base_ml: int, activity_minutes: int = 0) -> int:
        """Коррекция на физическую активность"""
        return base_ml + (activity_minutes * 10)
    
    @staticmethod
    def protein_correction(base_ml: int, daily_protein: int = 70) -> int:
        """Коррекция на белок"""
        return base_ml + (daily_protein * 7)
    
    @staticmethod
    def genetics_correction(base_ml: int, genetics: Dict[str, Any]) -> int:
        """Генетическая коррекция FTO"""
        fto = genetics.get('fto', '')
        if fto in ['AA', 'AT', '🔴 AA — высокий риск', '⚠️ AT — повышенный риск']:
            return int(base_ml * 1.1)
        return base_ml
    
    @staticmethod
    def cycle_correction(base_ml: int, user_data: Dict[str, Any]) -> int:
        """Коррекция на фазу цикла"""
        if user_data.get('gender_type') != 1:
            return base_ml
        
        from datetime import date
        today = date.today()
        cycle_start = date.fromisoformat(user_data['cycle_start'])
        cycle_length = user_data.get('cycle_length', 28)
        day = (today - cycle_start).days % cycle_length + 1
        
        if 17 <= day <= 24:
            return int(base_ml * 1.1)
        
        return base_ml
    
    @staticmethod
    def calculate_total(user_data: Dict[str, Any]) -> int:
        """Полный расчет с учетом всех факторов"""
        weight = user_data.get('weight', 70)
        if weight <= 0:
            weight = 70
        
        total = WaterCalculator.calculate_base(weight)
        
        if user_data.get('activity_minutes', 0):
            total = WaterCalculator.activity_correction(total, user_data['activity_minutes'])
        
        protein = user_data.get('daily_protein', 70)
        total = WaterCalculator.protein_correction(total, protein)
        
        genetics = {'fto': user_data.get('genetics_fto', '')}
        total = WaterCalculator.genetics_correction(total, genetics)
        
        total = WaterCalculator.cycle_correction(total, user_data)
        
        return total
    
    @staticmethod
    def get_schedule(total_ml: int, wake_hour: int = 7) -> List[Dict]:
        """Расписание питья (за 30 минут до еды)"""
        schedule = [
            {
                "time": f"{wake_hour:02d}:00",
                "name": "🌅 Гормональный старт",
                "ml": int(total_ml * 0.15),
                "type": "горячая с лимоном",
                "motilin": "🧹 Запуск домохозяйки"
            },
            {
                "time": f"{wake_hour+1:02d}:00",  # 👈 ЗА 30 МИН ДО ЗАВТРАКА (8:00)
                "name": "☀️ За 30 мин до завтрака",
                "ml": int(total_ml * 0.10),
                "type": "обычная",
                "motilin": "🍽️ Уборка перед завтраком"
            },
            {
                "time": "11:00",
                "name": "⚡ HIIT-подготовка",
                "ml": int(total_ml * 0.10),
                "type": "с электролитами",
                "motilin": "💪 Зарядка"
            },
            {
                "time": "12:30",  # 👈 ЗА 30 МИН ДО ОБЕДА (13:00)
                "name": "🥗 За 30 мин до обеда",
                "ml": int(total_ml * 0.10),
                "type": "обычная",
                "motilin": "🧹 Подготовка к обеду"
            },
            {
                "time": "15:30",
                "name": "💧 Детокс-удар (щелочная)",
                "ml": int(total_ml * 0.15),
                "type": "щелочная вода (pH 9-10.5)",
                "motilin": "💧 Пик работы почек — щелочная вода усиливает детоксикацию"
            },
            {
                "time": "17:30",  # 👈 ЗА 30 МИН ДО УЖИНА (18:00)
                "name": "🌿 За 30 мин до ужина",
                "ml": int(total_ml * 0.10),
                "type": "обычная",
                "motilin": "🧹 Финальная уборка"
            },
            {
                "time": "20:00",
                "name": "🧘 Вечерний баланс",
                "ml": int(total_ml * 0.15),
                "type": "теплая",
                "motilin": "🌙 Сдача смены"
            },
            {
                "time": "21:30",
                "name": "🌙 Финиш",
                "ml": int(total_ml * 0.05),
                "type": "небольшими глотками",
                "motilin": "😴 Ночная уборка"
            }
        ]
        return schedule
    
    @staticmethod
    def format_report(user_data: Dict[str, Any]) -> str:
        """Красивый отчет"""
        total = user_data.get('water_goal', WaterCalculator.calculate_total(user_data))
        consumed = user_data.get('water_consumed_today', 0)
        progress = min(100, int((consumed / total) * 100)) if total > 0 else 0
        
        bar = "█" * (progress // 10) + "░" * (10 - (progress // 10))
        
        report = f"""💧 **ВОДНЫЙ БАЛАНС**

    📊 **Сегодня:** {bar} {progress}%
    • Выпито: {consumed} / {total} мл
    • Осталось: {max(0, total - consumed)} мл

    🔬 **Факторы расчета:**
    • Вес: {user_data.get('weight', 70)} кг × 30 мл = {user_data.get('weight', 70)*30} мл
    """
    
        if user_data.get('activity_minutes', 0):
            report += f"• Активность: +{user_data.get('activity_minutes', 0)*10} мл\n"
        
        protein = user_data.get('daily_protein', 70)
        report += f"• Белок: +{protein*7} мл\n"
        
        fto = user_data.get('genetics_fto', '')
        if fto in ['AA', 'AT', '🔴 AA — высокий риск', '⚠️ AT — повышенный риск']:
            report += f"• Генетика FTO: +10% (риск обезвоживания)\n"
        
        from datetime import date
        today = date.today()
        if user_data.get('cycle_start'):
            try:
                cycle_start = date.fromisoformat(user_data['cycle_start'])
                cycle_length = user_data.get('cycle_length', 28)
                day = (today - cycle_start).days % cycle_length + 1
                if 17 <= day <= 24:
                    report += f"• Лютеиновая фаза: +10% (задержка воды)\n"
            except:
                pass
    
        report += f"""
    ⏰ **Расписание:** смотри в разделе "📅 Расписание"

    ⚠️ **ВАЖНО:**
    • Щелочная вода (pH 9-10.5) рекомендуется только после 15:00
    • Противопоказания: гастрит с пониженной кислотностью, язва, камни в почках
    • При любых хронических заболеваниях — консультация врача
    • Вода с кальцием — только после проверки уровня кальция в крови

    ℹ️ Подробнее — нажми "🧠 Как считается?"
    """
    
        return report


# ==================== ОБРАБОТЧИКИ ====================

@water_router.callback_query(F.data == "water_log")
async def water_log_callback(callback: types.CallbackQuery):
    """Отметить выпитый стакан"""
    # Импортируем ВНУТРИ функции
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
Мотилин — гормон, который запускает «волны чистки» в кишечнике.

**Как работает?**
Каждые 90-100 минут мотилин создает мощные сокращения.

**Связь с водой:**
Вода стимулирует выработку мотилина.

**Результат:**
✅ Нет вздутия
✅ Меньше ложного голода
✅ Лучшее усвоение пищи
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
• Генетика FTO: +10% для AA/AT
• Лютеиновая фаза: +10%
• Жара: +20%

💧 **ЩЕЛОЧНАЯ ВОДА ПОСЛЕ 15:00:**
• С 15:30 рекомендуется щелочная вода (pH 9-10.5)
• Пик работы почек (15-17 часов)
• Помогает нейтрализовать кислоты и выводить токсины

⚠️ **Важно:**
• Учитывается жидкость из еды
• Кофе и алкоголь требуют доп. воды

⚠️ **ВАЖНЫЕ ПРЕДУПРЕЖДЕНИЯ:**

🚫 **ЩЕЛОЧНАЯ ВОДА — ПРОТИВОПОКАЗАНИЯ:**
• Гастрит с пониженной кислотностью
• Язвенная болезнь желудка и двенадцатиперстной кишки
• Желчнокаменная болезнь
• Хроническая почечная недостаточность
• Прием некоторых лекарств (антациды, ингибиторы протонной помпы)
• Беременность и кормление грудью — ТОЛЬКО ПОСЛЕ КОНСУЛЬТАЦИИ С ВРАЧОМ

🥛 **ВОДА С КАЛЬЦИЕМ — ПРОТИВОПОКАЗАНИЯ:**
• Гиперкальциемия (повышенный кальций в крови)
• Мочекаменная болезнь (кальциевые камни)
• Саркоидоз
• Тяжелая почечная недостаточность
• Прием сердечных гликозидов
• Некоторые формы аритмии

👩‍⚕️ **КОМУ НЕОБХОДИМА КОНСУЛЬТАЦИЯ ВРАЧА:**
• Любые хронические заболевания почек
• Заболевания ЖКТ (гастрит, язва, панкреатит)
• Сердечно-сосудистые заболевания
• Беременность и лактация
• Детский и пожилой возраст
• Прием любых лекарственных препаратов

💡 **ОБЩИЕ РЕКОМЕНДАЦИИ:**
• Начинать с малых доз (50-100 мл) и следить за реакцией
• При появлении дискомфорта, тошноты, отеков — прекратить прием
• Учитывается жидкость из еды (супы, овощи, фрукты)
• Кофе и алкоголь требуют дополнительной воды

⚠️ *Данные рекомендации не являются медицинскими. Перед изменением питьевого режима проконсультируйтесь с врачом.*
"""
    await callback.message.answer(text)
    await callback.answer()
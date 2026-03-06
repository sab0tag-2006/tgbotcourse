# lunar.py - НАУЧНО-ОБРАЗОВАТЕЛЬНАЯ ВЕРСИЯ
"""
МОДУЛЬ ЛУННОГО ЦИКЛА
Четкое разделение: 🔬 доказательная наука | 📚 традиции и наблюдения
"""

import math
from datetime import datetime, timedelta

class LunarScience:
    """Научный подход к лунному циклу"""
    
    def __init__(self):
        # Фиксированные даты для расчета (первое новолуние 2026 года)
        self.first_new_moon_2026 = datetime(2026, 1, 18, 20, 52)
        self.lunar_cycle = 29.530588853  # длина лунного цикла в днях
        
        # Названия лунных дней (традиционные)
        self.lunar_day_names = {
            1: "🌑 Новолуние",
            2: "🌒 2-й лунный день",
            3: "🌒 3-й лунный день", 
            4: "🌒 4-й лунный день",
            5: "🌒 5-й лунный день",
            6: "🌒 6-й лунный день",
            7: "🌒 7-й лунный день",
            8: "🌓 Первая четверть",
            9: "🌓 9-й лунный день",
            10: "🌓 10-й лунный день",
            11: "🌓 11-й лунный день",
            12: "🌓 12-й лунный день",
            13: "🌓 13-й лунный день",
            14: "🌔 14-й лунный день",
            15: "🌕 Полнолуние",
            16: "🌕 16-й лунный день",
            17: "🌖 17-й лунный день",
            18: "🌖 18-й лунный день",
            19: "🌖 19-й лунный день",
            20: "🌖 20-й лунный день",
            21: "🌖 21-й лунный день",
            22: "🌗 Последняя четверть",
            23: "🌗 23-й лунный день",
            24: "🌘 24-й лунный день",
            25: "🌘 25-й лунный день",
            26: "🌘 26-й лунный день",
            27: "🌘 27-й лунный день",
            28: "🌘 28-й лунный день",
            29: "🌘 29-й лунный день",
            30: "🌑 30-й лунный день"
        }
    
    def get_phase(self, date=None):
        """
        Рассчитывает фазу Луны математически
        Возвращает фазу от 0 до 1, где 0 = новолуние, 0.5 = полнолуние
        """
        if date is None:
            date = datetime.now()
        
        # Разница в днях от известного новолуния
        delta = (date - self.first_new_moon_2026).total_seconds() / (24 * 3600)
        
        # Текущая фаза (0-1)
        phase = (delta % self.lunar_cycle) / self.lunar_cycle
        
        # Лунный день (1-30)
        lunar_day = int(delta % self.lunar_cycle) + 1
        if lunar_day > 30:
            lunar_day = 1
        
        # Освещенность: (1 - cos(2π * phase)) / 2
        illumination = (1 - math.cos(2 * math.pi * phase)) / 2
        
        # Название дня
        day_name = self.lunar_day_names.get(lunar_day, f"🌙 {lunar_day} лунный день")
        
        return {
            'phase': phase,
            'phase_percent': phase * 100,
            'illumination': illumination * 100,
            'lunar_day': lunar_day,
            'lunar_day_name': day_name,
            'next_full_moon': self._calculate_next_moon(date, 0.5),
            'next_new_moon': self._calculate_next_moon(date, 0.0)
        }
    
    def _calculate_next_moon(self, from_date, target_phase):
        """Вычисляет дату следующей нужной фазы (без рекурсии)"""
        # Разница в днях от известного новолуния
        delta = (from_date - self.first_new_moon_2026).total_seconds() / (24 * 3600)
        
        # Текущая фаза
        current_phase = (delta % self.lunar_cycle) / self.lunar_cycle
        
        # Разница до целевой фазы
        diff = (target_phase - current_phase) % 1.0
        if diff < 0:
            diff += 1.0
        
        # Дней до целевой фазы
        days_until = diff * self.lunar_cycle
        
        return from_date + timedelta(days=days_until)
    
    # ==================== 🔬 ДОКАЗАННАЯ НАУКА ====================
    
    def get_sleep_impact(self, phase_data):
        """
        🔬 ВЛИЯНИЕ НА СОН
        Cajochen et al. (2013) - Current Biology
        В полнолуние: -30% глубокого сна, +5 мин засыпание
        """
        phase = phase_data['phase']
        is_full = abs(phase - 0.5) < 0.1
        
        if is_full:
            return {
                'type': 'science',
                'title': '😴 ВЛИЯНИЕ НА СОН',
                'emoji': '🔬',
                'text': "Исследование Cajochen et al. (2013) показало: в полнолуние качество глубокого сна снижается на 30%, а время засыпания увеличивается на 5 минут.",
                'recommendation': "Ляг на 30 минут раньше и прими магний."
            }
        return None
    
    def get_hemostasis_impact(self, phase_data):
        """
        🔬 ВЛИЯНИЕ НА СЕРДЕЧНО-СОСУДИСТУЮ СИСТЕМУ
        Wende et al. (2013) - European Journal of Preventive Cardiology
        Карпушина (2013) - анализ вызовов скорой помощи
        """
        phase = phase_data['phase']
        
        is_full = abs(phase - 0.5) < 0.1
        is_new = phase < 0.03 or phase > 0.97
        
        if is_full or is_new:
            risk_period = "полнолуние" if is_full else "новолуние"
            
            return {
                'type': 'science',
                'title': '🩸 ВЛИЯНИЕ НА КРОВЬ И СОСУДЫ',
                'emoji': '🔬',
                'text': f"Исследования подтверждают: в {risk_period} повышается свертываемость крови и риск тромбообразования [Wende et al., 2013].\n\n"
                       f"📊 Статистика: в эти периоды чаще фиксируются вызовы скорой помощи с инфарктами и инсультами [Карпушина, 2013].",
                'recommendation': "• Пей больше воды (2-3 доп. стакана)\n"
                                 "• Добавь продукты, разжижающие кровь: черная смородина, горький шоколад\n"
                                 "• Избегай жирной пищи и алкоголя\n"
                                 "• Контролируй давление"
            }
        return None
    
    # ==================== 📚 ТРАДИЦИИ И НАБЛЮДЕНИЯ ====================
    
    def get_traditional_fluid_impact(self, phase_data):
        """
        📚 ТРАДИЦИОННЫЕ ПРЕДСТАВЛЕНИЯ О ВОДЕ
        Основано на народных наблюдениях о приливах и отливах
        """
        lunar_day = phase_data['lunar_day']
        
        if lunar_day in [29, 30, 1, 2]:
            return {
                'type': 'tradition',
                'title': '🌊 НАРОДНЫЕ НАБЛЮДЕНИЯ: ВОДА',
                'emoji': '📚',
                'text': "Согласно народным представлениям, в новолуние жидкость «уходит» из тканей.",
                'recommendation': "Хорошее время для детокса и лимфодренажа.\n"
                                 "Добавь мочегонные продукты: арбуз, огурец, сельдерей."
            }
        elif lunar_day in [14, 15, 16, 17]:
            return {
                'type': 'tradition',
                'title': '🌊 НАРОДНЫЕ НАБЛЮДЕНИЯ: ВОДА',
                'emoji': '📚',
                'text': "Согласно народным представлениям, в полнолуние жидкость задерживается в тканях.",
                'recommendation': "Контролируй соль, пей достаточно воды.\n"
                                 "Добавь калий: авокадо, курага, зелень."
            }
        return None
    
    def get_traditional_energy_impact(self, phase_data):
        """
        📚 ТРАДИЦИОННЫЕ ПРЕДСТАВЛЕНИЯ ОБ ЭНЕРГИИ
        Основано на лунных календарях и многовековых наблюдениях
        """
        lunar_day = phase_data['lunar_day']
        
        if lunar_day <= 7:
            return {
                'type': 'tradition',
                'title': '⚡ НАРОДНЫЕ НАБЛЮДЕНИЯ: ЭНЕРГИЯ',
                'emoji': '📚',
                'text': "По лунному календарю, растущая луна считается временем набора энергии.",
                'recommendation': "Традиционно это время рекомендуют для новых начинаний и проектов."
            }
        elif lunar_day <= 14:
            return {
                'type': 'tradition',
                'title': '⚡ НАРОДНЫЕ НАБЛЮДЕНИЯ: ЭНЕРГИЯ',
                'emoji': '📚',
                'text': "По лунному календарю, перед полнолунием энергия достигает пика.",
                'recommendation': "Время максимальной активности и свершений."
            }
        elif lunar_day <= 21:
            return {
                'type': 'tradition',
                'title': '⚡ НАРОДНЫЕ НАБЛЮДЕНИЯ: ЭНЕРГИЯ',
                'emoji': '📚',
                'text': "По лунному календарю, убывающая луна — время завершать дела.",
                'recommendation': "Рекомендуют снижать интенсивность и подводить итоги."
            }
        else:
            return {
                'type': 'tradition',
                'title': '⚡ НАРОДНЫЕ НАБЛЮДЕНИЯ: ЭНЕРГИЯ',
                'emoji': '📚',
                'text': "По лунному календарю, темная луна — время минимума энергии.",
                'recommendation': "Хорошее время для отдыха и восстановления."
            }
    
    def get_traditional_moon_advice(self, phase_data):
        """
        📚 ТРАДИЦИОННЫЕ РЕКОМЕНДАЦИИ ПО ЛУННЫМ ДНЯМ
        """
        lunar_day = phase_data['lunar_day']
        
        moon_advice = {
            1: "🌑 День новолуния — традиционно время загадывать желания и строить планы.",
            2: "🌒 День начала — хорошо для первых шагов к цели.",
            8: "🌓 Первая четверть — время принимать решения и действовать.",
            15: "🌕 Полнолуние — кульминация, время собирать урожай (результаты).",
            22: "🌗 Последняя четверть — время отдавать долги и завершать.",
            30: "🌑 30-й день — подведение итогов перед новым циклом."
        }
        
        if lunar_day in moon_advice:
            return {
                'type': 'tradition',
                'title': f'📆 ЛУННЫЙ ДЕНЬ {lunar_day}',
                'emoji': '📚',
                'text': moon_advice[lunar_day],
                'recommendation': ''
            }
        return None
    
    # ==================== СБОР ВСЕХ ДАННЫХ ====================
    
    def get_full_recommendation(self):
        """Объединяет научные данные и традиции с четкой маркировкой"""
        phase = self.get_phase()
        
        # 🔬 Научные данные
        sleep = self.get_sleep_impact(phase)
        hemo = self.get_hemostasis_impact(phase)
        
        # 📚 Традиции
        fluid = self.get_traditional_fluid_impact(phase)
        energy = self.get_traditional_energy_impact(phase)
        moon_day = self.get_traditional_moon_advice(phase)
        
        # Определяем фазу
        p = phase['phase']
        
        # Определяем, опасный ли период (научный факт)
        is_risk_period = (abs(p - 0.5) < 0.1) or (p < 0.03 or p > 0.97)
        risk_marker = " ⚠️ ПЕРИОД РИСКА (научные данные)" if is_risk_period else ""
        
        if p < 0.03 or p > 0.97:
            phase_name = f"НОВОЛУНИЕ{risk_marker}"
            phase_emoji = "🌑"
        elif p < 0.47:
            phase_name = "РАСТУЩАЯ ЛУНА"
            phase_emoji = "🌒"
        elif p <= 0.53:
            phase_name = f"ПОЛНОЛУНИЕ{risk_marker}"
            phase_emoji = "🌕"
        else:
            phase_name = "УБЫВАЮЩАЯ ЛУНА"
            phase_emoji = "🌘"
        
        # Собираем все разделы
        science_section = []
        traditions_section = []
        
        if sleep:
            science_section.append(f"{sleep['emoji']} **{sleep['title']}**\n{sleep['text']}\n💡 **Рекомендация:** {sleep['recommendation']}")
        
        if hemo:
            science_section.append(f"{hemo['emoji']} **{hemo['title']}**\n{hemo['text']}\n💡 **Рекомендация:**\n{hemo['recommendation']}")
        
        if fluid:
            traditions_section.append(f"{fluid['emoji']} **{fluid['title']}**\n{fluid['text']}\n💡 **Совет:** {fluid['recommendation']}")
        
        if energy:
            traditions_section.append(f"{energy['emoji']} **{energy['title']}**\n{energy['text']}\n💡 **Совет:** {energy['recommendation']}")
        
        if moon_day:
            traditions_section.append(f"{moon_day['emoji']} **{moon_day['title']}**\n{moon_day['text']}")
        
        return {
            'phase_name': phase_name,
            'phase_emoji': phase_emoji,
            'lunar_day': phase['lunar_day'],
            'lunar_day_name': phase['lunar_day_name'],
            'illumination': phase['illumination'],
            'science': science_section,
            'traditions': traditions_section
        }


def format_lunar_report(lunar_data):
    """Красиво форматирует отчет о Луне"""
    
    # Формируем научный раздел
    science_text = ""
    if lunar_data['science']:
        science_text = "\n🔬 **НАУЧНЫЕ ДАННЫЕ:**\n" + "\n".join(lunar_data['science']) + "\n"
    else:
        science_text = "\n🔬 **НАУЧНЫЕ ДАННЫЕ:**\nСегодня нет значимых научно доказанных лунных эффектов.\n"
    
    # Формируем раздел традиций
    traditions_text = ""
    if lunar_data['traditions']:
        traditions_text = "\n📚 **ТРАДИЦИИ И НАБЛЮДЕНИЯ:**\n" + "\n".join(lunar_data['traditions']) + "\n"
    
    text = f"""🌙 **ЛУННЫЙ КАЛЕНДАРЬ**
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

📅 **{lunar_data['lunar_day_name']}**
{lunar_data['phase_emoji']} **{lunar_data['phase_name']}**
Освещенность: {lunar_data['illumination']:.1f}%
{ science_text }
{ traditions_text }
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
📚 **Источники:**
🔬 **Научные:**
• Cajochen et al. (2013) - Current Biology (сон)
• Wende et al. (2013) - European Journal of Preventive Cardiology (сердечно-сосудистые риски)
• Карпушина (2013) - ВАК (статистика скорой помощи)

📚 **Традиционные:** многовековые наблюдения и лунные календари разных культур
"""
    
    return text
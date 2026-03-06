# cycle_integration.py - ИНТЕГРАЦИЯ ТРЕХ ЦИКЛОВ
from datetime import date
from lunar import LunarScience
from rhythm_core import get_female_phase, get_cns_phase

class CycleIntegrator:
    """Объединяет три цикла: лунный, женский и ЦНС"""
    
    def __init__(self, user_data):
        self.user = user_data
        self.lunar = LunarScience()
        self.today = date.today()
    
    def get_lunar_phase(self):
        """Получает фазу луны"""
        phase_data = self.lunar.get_phase()
        p = phase_data['phase']
        
        if abs(p - 0.5) < 0.1:
            return "full_moon"  # Полнолуние
        elif p < 0.03 or p > 0.97:
            return "new_moon"   # Новолуние
        elif p < 0.5:
            return "waxing"     # Растущая
        else:
            return "waning"      # Убывающая
    
    def get_cycle_phase(self):
        """Получает фазу женского цикла"""
        if self.user.get('gender_type') != 1:
            return None
        
        cycle_start = date.fromisoformat(self.user['cycle_start'])
        cycle_length = self.user.get('cycle_length', 28)
        day = (self.today - cycle_start).days % cycle_length + 1
        
        if 1 <= day <= 5:
            return "menstrual"
        elif 6 <= day <= 12:
            return "follicular"
        elif 13 <= day <= 16:
            return "ovulation"
        elif 17 <= day <= 24:
            return "luteal"
        else:
            return "pms"
    
    def get_cns_phase_type(self):
        """Получает тип фазы ЦНС"""
        rhythm_start = date.fromisoformat(self.user['rhythm_start'])
        cns_day = (self.today - rhythm_start).days % 9 + 1
        
        if cns_day <= 3:
            return "peak"      # Пик
        elif cns_day <= 6:
            return "stable"    # Стабильно
        else:
            return "detox"     # Детокс/отдых
    
    def get_energy_level(self):
        """Определяет уровень энергии по циклам"""
        cycle = self.get_cycle_phase()
        cns = self.get_cns_phase_type()
        
        energy_score = 100  # базовая энергия
        
        # Коррекция по циклу
        if cycle == "menstrual":
            energy_score -= 30
        elif cycle == "follicular":
            energy_score += 10
        elif cycle == "ovulation":
            energy_score += 20
        elif cycle == "luteal":
            energy_score -= 10
        elif cycle == "pms":
            energy_score -= 20
        
        # Коррекция по ЦНС
        if cns == "peak":
            energy_score += 20
        elif cns == "detox":
            energy_score -= 20
        
        # Ограничиваем от 0 до 100
        energy_score = max(0, min(100, energy_score))
        
        # Возвращаем со стрелочками
        if energy_score >= 80:
            return f"⬆️⬆️ ВЫСОКАЯ ({energy_score}%)"
        elif energy_score >= 60:
            return f"⬆️ ХОРОШАЯ ({energy_score}%)"
        elif energy_score >= 40:
            return f"➡️ СРЕДНЯЯ ({energy_score}%)"
        elif energy_score >= 20:
            return f"⬇️ ПОНИЖЕННАЯ ({energy_score}%)"
        else:
            return f"⬇️⬇️ НИЗКАЯ ({energy_score}%)"
    
    def get_risk_level(self):
        """Определяет уровень риска по всем циклам"""
        lunar = self.get_lunar_phase()
        cycle = self.get_cycle_phase()
        cns = self.get_cns_phase_type()
        
        # Матрица рисков
        risk_score = 0
        details_lines = []
        
        # Лунные риски
        if lunar == "full_moon":
            risk_score += 3
            details_lines.append("🌕 Полнолуние (+3)")
        elif lunar == "new_moon":
            risk_score += 2
            details_lines.append("🌑 Новолуние (+2)")
        else:
            details_lines.append("🌙 Обычная фаза (+0)")
        
        # Циклические риски
        if cycle == "menstrual":
            risk_score += 3
            details_lines.append("🩸 Менструация (+3)")
        elif cycle == "pms":
            risk_score += 2
            details_lines.append("🍂 ПМС (+2)")
        elif cycle == "luteal":
            risk_score += 1
            details_lines.append("🌿 Лютеиновая (+1)")
        elif cycle:
            details_lines.append("🌱 Безопасная фаза (+0)")
        else:
            details_lines.append("👩 Женщина (без цикла) / 👨 Мужчина (+0)")
        
        # Риски ЦНС
        if cns == "detox":
            risk_score += 2
            details_lines.append("🧹 Детокс ЦНС (+2)")
        else:
            details_lines.append("⚡ Активная ЦНС (+0)")
        
        details = "\n".join(details_lines)
        
        # Определяем уровень
        if risk_score >= 6:
            return {
                "level": "🔴 КРИТИЧЕСКИЙ",
                "emoji": "🚨",
                "water": "+50%",
                "activity": "❌ ПОЛНЫЙ ОТДЫХ",
                "score": risk_score,
                "details": details,
                "advice": "⚠️ СЕГОДНЯ ТРОЙНОЙ ФАКТОР РИСКА!\n• Кровь максимально густая\n• Высокий риск тромбов\n• Пей 3+ литра воды\n• Никаких тренировок\n• Только покой"
            }
        elif risk_score >= 4:
            return {
                "level": "🟠 ВЫСОКИЙ",
                "emoji": "⚠️",
                "water": "+30%",
                "activity": "⚡ ЛЕГКАЯ",
                "score": risk_score,
                "details": details,
                "advice": "Повышенная вязкость крови. Пей больше воды, избегай интенсивных тренировок."
            }
        elif risk_score >= 2:
            return {
                "level": "🟡 СРЕДНИЙ",
                "emoji": "👀",
                "water": "+10%",
                "activity": "✅ УМЕРЕННАЯ",
                "score": risk_score,
                "details": details,
                "advice": "Обрати внимание на питьевой режим. Можно тренироваться в умеренном режиме."
            }
        else:
            return {
                "level": "🟢 НОРМА",
                "emoji": "✅",
                "water": "0%",
                "activity": "💪 ПОЛНАЯ",
                "score": risk_score,
                "details": details,
                "advice": "Хороший день для активности. Все системы в балансе."
            }
    
    def get_daily_risk_report(self):
        """Формирует отчет по рискам"""
        lunar = self.get_lunar_phase()
        cycle = self.get_cycle_phase()
        cns = self.get_cns_phase_type()
        risk = self.get_risk_level()
        
        # Функция для получения стрелочки энергии
        def get_energy_arrow(phase_type):
            arrows = {
                "peak": "⬆️⬆️ МАКСИМУМ",
                "stable": "⬆️ СТАБИЛЬНО",
                "detox": "⬇️ СНИЖЕНИЕ"
            }
            return arrows.get(phase_type, "➡️ НОРМА")
        
        # Названия фаз с красивыми стрелочками
        lunar_names = {
            "full_moon": "🌕 ПОЛНОЛУНИЕ ⬆️⬆️ (вязкость ↑↑)",
            "new_moon": "🌑 НОВОЛУНИЕ ⬆️ (вязкость ↑)",
            "waxing": "🌒 РАСТУЩАЯ ➡️ (норма)",
            "waning": "🌘 УБЫВАЮЩАЯ ➡️ (норма)"
        }
        
        cycle_names = {
            "menstrual": "🩸 МЕНСТРУАЦИЯ ⬆️⬆️ (вязкость ↑↑)",
            "follicular": "🌱 ФОЛЛИКУЛЯРНАЯ ⬆️ (энергия ↑)",
            "ovulation": "⚡ ОВУЛЯЦИЯ ⬆️⬆️ (пик)",
            "luteal": "🌿 ЛЮТЕИНОВАЯ ⬇️ (спад)",
            "pms": "🍂 ПМС ⬆️ (вязкость ↑) ⬇️ (энергия ↓)"
        }
        
        cns_names = {
            "peak": f"⚡ ПИК ЦНС {get_energy_arrow('peak')}",
            "stable": f"📊 СТАБИЛЬНОСТЬ ЦНС {get_energy_arrow('stable')}",
            "detox": f"🧹 ДЕТОКС ЦНС {get_energy_arrow('detox')}"
        }
        
        report = f"""🌕🩸🧠 **ИНТЕГРАЛЬНЫЙ РИСК-АНАЛИЗ**
⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯

🌙 **ЛУНА:** {lunar_names.get(lunar, '')}
🩸 **ЦИКЛ:** {cycle_names.get(cycle, '') if cycle else '👩 Женщина (без цикла) / 👨 Мужчина'}
🧠 **ЦНС:** {cns_names.get(cns, '')}

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
{risk['emoji']} **УРОВЕНЬ РИСКА: {risk['level']}** (баллы: {risk['score']})

{risk['details']}

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
💧 **ВОДА:** {risk['water']} к норме
⚡ **ЭНЕРГИЯ:** {self.get_energy_level()}
💪 **АКТИВНОСТЬ:** {risk['activity']}

📋 **РЕКОМЕНДАЦИЯ:**
{risk['advice']}

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯
⚠️ *Основано на научных исследованиях*
"""
        return report
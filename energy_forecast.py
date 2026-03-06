# energy_forecast.py
from datetime import date, timedelta, datetime
from typing import List, Dict
import matplotlib.pyplot as plt
import io
import math
from rhythm_core import get_female_phase, get_cns_phase
from lunar import LunarScience

class EnergyForecast:
    """Прогноз энергии на основе циклов"""
    
    def __init__(self, user_data):
        self.user = user_data
        self.today = date.today()
        self.lunar = LunarScience()
    
    def get_age_group(self, age: int) -> str:
        """Определяет группу по возрасту"""
        if age < 35:
            return "young"
        elif age < 45:
            return "pre_peri"
        elif age < 55:
            return "peri"
        else:
            return "post"
    
    def get_daily_energy(self, target_date: date) -> Dict:
        """Рассчитывает энергию на конкретный день для женщин с циклом"""
        
        # Базовая энергия от цикла (0-100)
        if self.user.get('gender_type') == 1:
            cycle_start = date.fromisoformat(self.user['cycle_start'])
            cycle_length = self.user.get('cycle_length', 28)
            cycle_day = (target_date - cycle_start).days % cycle_length + 1
            phase = get_female_phase(cycle_day, cycle_length)
            cycle_energy = phase['energy'] * 100
        else:
            cycle_energy = 70  # для мужчин база
        
        # Коррекция по ЦНС
        rhythm_start = date.fromisoformat(self.user['rhythm_start'])
        cns_day = (target_date - rhythm_start).days % 9 + 1
        cns = get_cns_phase(cns_day)
        cns_factor = cns['energy']
        
        # Коррекция по луне
        target_datetime = datetime.combine(target_date, datetime.min.time())
        phase_data = self.lunar.get_phase(target_datetime)
        p = phase_data['phase']
        
        is_full_moon = abs(p - 0.5) < 0.1
        is_new_moon = p < 0.03 or p > 0.97
        
        lunar_factor = 1.0
        if is_full_moon:
            lunar_factor = 0.9  # -10% в полнолуние
        elif is_new_moon:
            lunar_factor = 0.95  # -5% в новолуние
        
        # Итоговая энергия
        total_energy = int(cycle_energy * cns_factor * lunar_factor)
        
        # Определяем уровень
        if total_energy >= 80:
            level = "🔴 ВЫСОКАЯ"
            activity = "⚡ Максимальные нагрузки, HIIT, рекорды"
            recovery = "😴 7-8 часов сна"
        elif total_energy >= 60:
            level = "🟡 СРЕДНЯЯ"
            activity = "🏃‍♀️ Умеренные тренировки, работа"
            recovery = "😴 8 часов сна"
        elif total_energy >= 40:
            level = "🟢 НОРМАЛЬНАЯ"
            activity = "🧘 Легкая активность, прогулки"
            recovery = "😴 8-9 часов сна"
        else:
            level = "🔵 НИЗКАЯ"
            activity = "🛌 Отдых, восстановление"
            recovery = "😴 9+ часов сна"
        
        return {
            'date': target_date,
            'energy': total_energy,
            'level': level,
            'activity': activity,
            'recovery': recovery,
            'cycle_day': cycle_day if self.user.get('gender_type') == 1 else None,
            'cns_day': cns_day,
            'phase': phase['name'] if self.user.get('gender_type') == 1 else None
        }
    
    def get_daily_energy_no_cycle(self, target_date: date) -> Dict:
        """Рассчитывает энергию для женщин без цикла"""
        
        # Получаем возраст (можно добавить поле в регистрацию)
        age = self.user.get('age', 45)
        
        # ===== 1. БАЗОВАЯ ЭНЕРГИЯ ПО ВОЗРАСТУ =====
        if age < 40:
            base_energy = 70
        elif age < 50:
            # Перименопауза — нестабильная энергия
            day_of_year = target_date.timetuple().tm_yday
            base_energy = 50 + 20 * math.sin(day_of_year / 30)
        else:
            # Менопауза — стабильно низкая база
            base_energy = 50
        
        # ===== 2. КОРРЕКЦИЯ ПО ЦНС =====
        rhythm_start = date.fromisoformat(self.user['rhythm_start'])
        cns_day = (target_date - rhythm_start).days % 9 + 1
        cns = get_cns_phase(cns_day)
        cns_factor = cns['energy']
        
        # ===== 3. КОРРЕКЦИЯ ПО ЛУНЕ =====
        target_datetime = datetime.combine(target_date, datetime.min.time())
        phase_data = self.lunar.get_phase(target_datetime)
        p = phase_data['phase']
        
        lunar_factor = 1.0
        if abs(p - 0.5) < 0.1:
            lunar_factor = 0.9
        elif p < 0.03 or p > 0.97:
            lunar_factor = 0.95
        
        # ===== 4. КОРРЕКЦИЯ ПО СЕЗОНУ =====
        month = target_date.month
        if month in [12, 1, 2]:
            season_factor = 0.85
        elif month in [6, 7, 8]:
            season_factor = 1.1
        else:
            season_factor = 1.0
        
        # ===== 5. ИТОГОВАЯ ЭНЕРГИЯ =====
        total_energy = int(base_energy * cns_factor * lunar_factor * season_factor)
        
        # Определяем уровень
        if total_energy >= 70:
            level = "🔴 ВЫСОКАЯ"
            activity = "⚡ Можно активничать"
        elif total_energy >= 50:
            level = "🟡 СРЕДНЯЯ"
            activity = "🏃‍♀️ Умеренная нагрузка"
        elif total_energy >= 35:
            level = "🟢 НОРМАЛЬНАЯ"
            activity = "🧘 Легкая активность"
        else:
            level = "🔵 НИЗКАЯ"
            activity = "🛌 Отдых"
        
        return {
            'date': target_date,
            'energy': total_energy,
            'level': level,
            'activity': activity,
            'cns_day': cns_day,
            'age_group': self.get_age_group(age)
        }
    
    def get_week_forecast(self) -> List[Dict]:
        """Прогноз на 7 дней для женщин с циклом"""
        forecast = []
        for i in range(7):
            day = self.today + timedelta(days=i)
            forecast.append(self.get_daily_energy(day))
        return forecast
    
    def get_week_forecast_no_cycle(self) -> List[Dict]:
        """Прогноз на 7 дней для женщин без цикла"""
        forecast = []
        for i in range(7):
            day = self.today + timedelta(days=i)
            forecast.append(self.get_daily_energy_no_cycle(day))
        return forecast
    
    def get_month_forecast(self) -> List[Dict]:
        """Прогноз на 28 дней с защитой от ошибок"""
        forecast = []
        try:
            if self.user.get('gender_type') == 1:
                for i in range(28):
                    day = self.today + timedelta(days=i)
                    forecast.append(self.get_daily_energy(day))
            else:
                for i in range(28):
                    day = self.today + timedelta(days=i)
                    forecast.append(self.get_daily_energy_no_cycle(day))
        except Exception as e:
            print(f"❌ Ошибка в get_month_forecast: {e}")
            return []
        return forecast
    
    def plot_week_energy(self) -> io.BytesIO:
        """Создает график энергии на неделю"""
        if self.user.get('gender_type') == 1:
            forecast = self.get_week_forecast()
        else:
            forecast = self.get_week_forecast_no_cycle()
        
        dates = [d['date'].strftime('%d.%m') for d in forecast]
        energies = [d['energy'] for d in forecast]
        
        fig, ax = plt.subplots(figsize=(10, 5))
        
        # Цвета в зависимости от уровня
        colors = []
        for e in energies:
            if e >= 70:
                colors.append('#ff4444')  # красный
            elif e >= 50:
                colors.append('#ffaa44')  # оранжевый
            elif e >= 35:
                colors.append('#44ff44')  # зеленый
            else:
                colors.append('#4444ff')  # синий
        
        bars = ax.bar(dates, energies, color=colors, alpha=0.7)
        ax.set_ylim(0, 100)
        ax.set_ylabel('Энергия (%)')
        ax.set_title('Прогноз энергии на неделю')
        ax.grid(True, alpha=0.3)
        
        # Добавляем значения на столбцы
        for bar, e in zip(bars, energies):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                   f'{e}%', ha='center', va='bottom')
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf


# ==================== ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ====================

def check_future_critical(forecast: List[Dict], days_ahead: int = 14) -> Dict:
    """
    Анализирует прогноз и ищет критические периоды в будущем
    Возвращает словарь с предупреждением
    """
    warning = {
        'has_critical': False,
        'critical_days': [],
        'start_day': None,
        'end_day': None,
        'days_until': None,
        'severity': 'low'
    }
    
    # Ищем периоды, где 3+ дня подряд энергия < 30%
    critical_sequence = []
    for i, day in enumerate(forecast[:days_ahead]):
        if day['energy'] < 30:
            critical_sequence.append(day)
        else:
            if len(critical_sequence) >= 3:
                warning['has_critical'] = True
                warning['critical_days'] = critical_sequence
                warning['start_day'] = critical_sequence[0]['date']
                warning['end_day'] = critical_sequence[-1]['date']
                warning['days_until'] = i - len(critical_sequence)
                warning['severity'] = 'high' if any(d['energy'] < 15 for d in critical_sequence) else 'medium'
                break
            critical_sequence = []
    
    return warning


def get_future_warning_message(forecast: List[Dict]) -> str:
    """Формирует предупреждение о будущем кризисе"""
    warning = check_future_critical(forecast)
    
    if not warning['has_critical']:
        return ""
    
    # Строим визуализацию прогноза
    forecast_text = ""
    for i, day in enumerate(forecast[:14]):
        if day['energy'] >= 70:
            emoji = "🔴"
        elif day['energy'] >= 50:
            emoji = "🟡"
        elif day['energy'] >= 35:
            emoji = "🟢"
        else:
            emoji = "🔵"
        
        day_text = f"{emoji} {day['date'].strftime('%d.%m')}: {day['energy']}%"
        
        # Отмечаем критические дни
        if day in warning['critical_days']:
            day_text += " ⚠️ КРИТИЧЕСКИЙ"
        
        forecast_text += day_text + "\n"
    
    # Формируем рекомендации по подготовке
    prep_text = ""
    if warning['days_until'] > 7:
        prep_text = f"""
📅 **ЗА {warning['days_until']} ДНЕЙ ДО КРИЗИСА (сейчас):**
• Запасись костным бульоном (свари и заморозь)
• Купи магний и английскую соль
• Предупреди семью/работу, что будешь на "тихом режиме"
"""
    elif warning['days_until'] > 3:
        prep_text = f"""
📅 **ЗА {warning['days_until']} ДНЯ ДО КРИЗИСА:**
• Начни снижать нагрузку
• Переходи на теплую еду
• Готовься к отдыху
"""
    else:
        prep_text = f"""
📅 **КРИЗИС НАЧНЕТСЯ ЧЕРЕЗ {warning['days_until']} ДНЯ!**
• СРОЧНО начинай SAFE MODE
• Отмени все важные дела
• Только отдых и восстановление
"""
    
    text = f"""
🚨 **ПРЕДУПРЕЖДЕНИЕ: КРИТИЧЕСКАЯ НЕДЕЛЯ ЧЕРЕЗ {warning['days_until']} ДНЕЙ!**

📊 Прогноз энергии на ближайшие 14 дней:

{forecast_text}

⚠️ **С {warning['start_day'].strftime('%d.%m')} по {warning['end_day'].strftime('%d.%m')} — критическая зона!**
   Энергия будет ниже 30% {len(warning['critical_days'])} ДНЯ ПОДРЯД.

🛡️ **ГОТОВЬСЯ ЗАРАНЕЕ:**
{prep_text}

💡 **В критической зоне:**
• Полный отдых
• Только бульоны и тепло
• Никаких важных решений
• Никакого самобичевания

*Это не слабость. Это биология. Твой цикл предсказуем — используй это знание.*
"""
    return text
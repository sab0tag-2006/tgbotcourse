# statistics.py - МОДУЛЬ СТАТИСТИКИ
"""
Модуль для анализа данных и построения графиков
"""

import sqlite3
import matplotlib.pyplot as plt
import matplotlib
matplotlib.use('Agg')  # для работы без GUI
import io
import pandas as pd
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional
import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
import tempfile

# ИМПОРТЫ ДЛЯ TELEGRAM
from aiogram import types
from aiogram.utils.keyboard import InlineKeyboardBuilder

DB_NAME = 'users.db'

class StatisticsModule:
    """Модуль статистики и аналитики"""
    
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.user_data = self._get_user_data()
    
    def _get_user_data(self):
        """Получает данные пользователя"""
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("SELECT * FROM users WHERE user_id = ?", (self.user_id,))
            result = cur.fetchone()
            return dict(result) if result else {}
    
    # ==================== СБОР ДАННЫХ ====================
    
    def get_morning_data(self, days: int = 30) -> List[Dict]:
        """Получает данные утренних замеров"""
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM morning_checkin 
                WHERE user_id = ? 
                ORDER BY date DESC 
                LIMIT ?
            """, (self.user_id, days))
            return [dict(row) for row in cur.fetchall()]
    
    def get_evening_data(self, days: int = 30) -> List[Dict]:
        """Получает данные вечерних аудитов"""
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM evening_audit 
                WHERE user_id = ? 
                ORDER BY date DESC 
                LIMIT ?
            """, (self.user_id, days))
            return [dict(row) for row in cur.fetchall()]
    
    def get_weekly_data(self, months: int = 3) -> List[Dict]:
        """Получает данные недельных замеров"""
        with sqlite3.connect(DB_NAME) as conn:
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute("""
                SELECT * FROM weekly_metrics 
                WHERE user_id = ? 
                ORDER BY date DESC 
                LIMIT ?
            """, (self.user_id, months * 4))
            return [dict(row) for row in cur.fetchall()]
    
    # ==================== ГРАФИКИ ====================
    
    def plot_pulse_delta(self, days: int = 14) -> Optional[io.BytesIO]:
        """
        График дельты пульса (ортопроба)
        Показывает восстановление ЦНС
        """
        data = self.get_morning_data(days)
        
        if not data:
            return None
        
        # Разворачиваем для хронологического порядка
        data.reverse()
        
        dates = [d['date'][5:] for d in data]  # только месяц-день
        deltas = [d['pulse_delta'] for d in data]
        sleep = [d['sleep_quality'] for d in data]
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 8))
        fig.suptitle(f'Анализ восстановления ЦНС (последние {len(data)} дней)', fontsize=14)
        
        # График дельты пульса
        ax1.plot(dates, deltas, 'b-o', linewidth=2, markersize=4)
        ax1.axhline(y=20, color='r', linestyle='--', alpha=0.5, label='Критический уровень')
        ax1.axhline(y=15, color='orange', linestyle='--', alpha=0.5, label='Пограничный уровень')
        ax1.set_ylabel('Дельта пульса (уд/мин)')
        ax1.set_title('Ортопроба (пульс лежа → стоя)')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # Закрашиваем опасные зоны
        ax1.fill_between(dates, 20, max(deltas + [20]), color='red', alpha=0.1)
        ax1.fill_between(dates, 15, 20, color='orange', alpha=0.1)
        
        # График качества сна
        ax2.bar(dates, sleep, color='skyblue', alpha=0.7)
        ax2.set_ylabel('Качество сна (1-5)')
        ax2.set_title('Качество сна')
        ax2.grid(True, alpha=0.3)
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        # Сохраняем в буфер
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    
    def plot_cycle_phases(self) -> Optional[io.BytesIO]:
        """
        Визуализация фаз цикла
        """
        if self.user_data.get('gender_type') != 1:
            return None
        
        from rhythm_core import get_female_phase
        
        # Берем последние 2 цикла
        cycle_length = self.user_data.get('cycle_length', 28)
        total_days = cycle_length * 2
        
        dates = []
        energies = []
        phases = []
        
        cycle_start = date.fromisoformat(self.user_data['cycle_start'])
        
        for i in range(total_days):
            current_date = cycle_start + timedelta(days=i)
            if current_date > date.today():
                break
            
            day = i % cycle_length + 1
            phase = get_female_phase(day, cycle_length)
            
            dates.append(current_date.strftime('%d.%m'))
            energies.append(phase['energy'] * 100)
            phases.append(phase['name'][:4])  # сокращенно
        
        if not dates:
            return None
        
        fig, ax = plt.subplots(figsize=(12, 5))
        fig.suptitle('Энергия по фазам цикла', fontsize=14)
        
        # Цвета для разных фаз
        colors_map = {
            'Менс': '#ff9999',
            'Фолл': '#66b3ff',
            'Овул': '#99ff99',
            'Лют': '#ffcc99',
            'ПМС': '#ff6666'
        }
        
        bars = ax.bar(dates, energies, alpha=0.7)
        
        # Окрашиваем бары в зависимости от фазы
        for i, (bar, phase) in enumerate(zip(bars, phases)):
            color = colors_map.get(phase, '#cccccc')
            bar.set_color(color)
        
        ax.set_ylabel('Энергия (%)')
        ax.set_xlabel('Дата')
        ax.grid(True, alpha=0.3)
        ax.axhline(y=50, color='gray', linestyle='--', alpha=0.5)
        
        # Легенда
        from matplotlib.patches import Patch
        legend_elements = [
            Patch(facecolor='#ff9999', label='Менструация'),
            Patch(facecolor='#66b3ff', label='Фолликулярная'),
            Patch(facecolor='#99ff99', label='Овуляция'),
            Patch(facecolor='#ffcc99', label='Лютеиновая'),
            Patch(facecolor='#ff6666', label='ПМС')
        ]
        ax.legend(handles=legend_elements, loc='upper right')
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    
    def plot_hiit_compliance(self, months: int = 3) -> Optional[io.BytesIO]:
        """
        График выполнения HIIT тренировок
        """
        evening_data = self.get_evening_data(months * 30)
        
        if not evening_data:
            return None
        
        # Группируем по месяцам
        monthly_stats = {}
        for entry in evening_data:
            month = entry['date'][:7]  # ГГГГ-ММ
            if month not in monthly_stats:
                monthly_stats[month] = {'total': 0, 'done': 0}
            
            monthly_stats[month]['total'] += 1
            if entry.get('hiit_done'):
                monthly_stats[month]['done'] += 1
        
        months_list = sorted(monthly_stats.keys())
        compliance = []
        
        for month in months_list:
            stats = monthly_stats[month]
            if stats['total'] > 0:
                compliance.append((stats['done'] / stats['total']) * 100)
            else:
                compliance.append(0)
        
        if not months_list:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.suptitle('Выполнение HIIT тренировок', fontsize=14)
        
        bars = ax.bar(months_list, compliance, color='#ff9999', alpha=0.7)
        ax.set_ylabel('Выполнение (%)')
        ax.set_ylim(0, 100)
        ax.grid(True, alpha=0.3)
        ax.axhline(y=70, color='green', linestyle='--', alpha=0.5, label='Целевой уровень')
        ax.legend()
        
        # Добавляем значения на столбцы
        for bar, val in zip(bars, compliance):
            height = bar.get_height()
            ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                   f'{val:.0f}%', ha='center', va='bottom')
        
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    
    def plot_weight_trend(self) -> Optional[io.BytesIO]:
        """
        График изменения веса
        """
        weekly = self.get_weekly_data(6)  # полгода
        
        if not weekly:
            return None
        
        weekly.reverse()
        
        dates = [w['date'][5:] for w in weekly]  # только месяц-день
        weights = [w['weight'] for w in weekly if w['weight'] > 0]
        
        if len(weights) < 2:
            return None
        
        fig, ax = plt.subplots(figsize=(10, 5))
        fig.suptitle('Динамика веса', fontsize=14)
        
        ax.plot(dates[:len(weights)], weights, 'g-o', linewidth=2, markersize=6)
        ax.set_ylabel('Вес (кг)')
        ax.grid(True, alpha=0.3)
        
        # Линия тренда
        if len(weights) > 2:
            import numpy as np
            x = np.arange(len(weights))
            z = np.polyfit(x, weights, 1)
            p = np.poly1d(z)
            ax.plot(dates[:len(weights)], p(x), 'r--', alpha=0.7, label='Тренд')
            ax.legend()
        
        plt.xticks(rotation=45)
        plt.tight_layout()
        
        buf = io.BytesIO()
        plt.savefig(buf, format='png', dpi=100)
        buf.seek(0)
        plt.close()
        
        return buf
    
    # ==================== ЭКСПОРТ В ТЕКСТ ====================
    
    def generate_txt_report(self) -> Optional[str]:
        """
        Генерирует текстовый отчет со всей статистикой
        """
        # Создаем временный текстовый файл
        fd, path = tempfile.mkstemp(suffix='.txt')
        os.close(fd)
        
        # Получаем данные
        morning = self.get_morning_data(30)
        evening = self.get_evening_data(30)
        weekly = self.get_weekly_data(3)
        
        # Формируем текстовый отчет
        report = []
        report.append("=" * 60)
        report.append("📊 ОТЧЕТ ПО СИСТЕМЕ «КОД РЕВЕРС»".center(58))
        report.append("=" * 60)
        report.append(f"📅 Имя силы: {self.user_data.get('power_name', '')}")
        report.append(f"📅 Дата отчета: {datetime.now().strftime('%d.%m.%Y %H:%M')}")
        report.append("=" * 60)
        report.append("")
        
        # Информация о пользователе
        report.append("👤 ИНФОРМАЦИЯ О ПОЛЬЗОВАТЕЛЕ:")
        report.append("-" * 40)
        report.append(f"Пол: {'Женщина' if self.user_data.get('gender_type') == 1 else 'Мужчина'}")
        report.append(f"Вес: {self.user_data.get('weight', 0)} кг")
        report.append(f"Пульс покоя: {self.user_data.get('resting_hr', 0)} уд/мин")
        report.append(f"Время пробуждения: {self.user_data.get('wake_time', '')}")
        report.append(f"Тип работы: {self.user_data.get('work_type', 'Не указано')}")
        report.append("")
        
        # Статистика активности
        report.append("📈 СТАТИСТИКА АКТИВНОСТИ:")
        report.append("-" * 40)
        report.append(f"Утренних замеров: {len(morning)}")
        report.append(f"Вечерних аудитов: {len(evening)}")
        report.append(f"Недельных замеров: {len(weekly)}")
        report.append(f"Всего записей: {len(morning) + len(evening) + len(weekly)}")
        report.append("")
        
        # Показатели здоровья
        if morning:
            avg_sleep = sum(m['sleep_quality'] for m in morning) / len(morning)
            avg_delta = sum(m['pulse_delta'] for m in morning) / len(morning)
            
            report.append("❤️ ПОКАЗАТЕЛИ ЗДОРОВЬЯ:")
            report.append("-" * 40)
            report.append(f"Качество сна (среднее): {avg_sleep:.1f}/5")
            
            if avg_sleep >= 4:
                report.append("  🟢 Отлично")
            elif avg_sleep >= 3:
                report.append("  🟡 Средне")
            else:
                report.append("  🔴 Плохо")
            
            report.append(f"Дельта пульса (средняя): {avg_delta:.1f} уд/мин")
            
            if avg_delta <= 15:
                report.append("  🟢 Норма")
            elif avg_delta <= 20:
                report.append("  🟡 Погранично")
            else:
                report.append("  🔴 Перегруз")
            report.append("")
        
        # Тренировки и мотивация
        if evening:
            avg_motivation = sum(e.get('motivation', 0) for e in evening) / len(evening)
            avg_energy = sum(e.get('energy', 0) for e in evening) / len(evening)
            hiit_count = sum(1 for e in evening if e.get('hiit_done', 0))
            
            report.append("💪 ТРЕНИРОВКИ И МОТИВАЦИЯ:")
            report.append("-" * 40)
            report.append(f"Средняя мотивация: {avg_motivation:.1f}/5")
            report.append(f"Средняя энергия: {avg_energy:.1f}/5")
            report.append(f"HIIT выполнено: {hiit_count} из {len(evening)} ({hiit_count/len(evening)*100:.0f}%)")
            report.append("")
        
        # Динамика веса
        if weekly and any(w['weight'] > 0 for w in weekly):
            valid_weights = [w['weight'] for w in weekly if w['weight'] > 0]
            if valid_weights:
                first_weight = valid_weights[0]
                last_weight = valid_weights[-1]
                change = last_weight - first_weight
                
                report.append("⚖️ ДИНАМИКА ВЕСА:")
                report.append("-" * 40)
                report.append(f"Начальный вес: {first_weight:.1f} кг")
                report.append(f"Текущий вес: {last_weight:.1f} кг")
                report.append(f"Изменение: {change:+.1f} кг ")
                
                if change < -1:
                    report.append("  📉 Хорошее снижение")
                elif change < 0:
                    report.append("  📉 Небольшое снижение")
                elif change > 1:
                    report.append("  📈 Заметный рост")
                elif change > 0:
                    report.append("  📈 Небольшой рост")
                else:
                    report.append("  ➡️ Стабильно")
                report.append("")
        
        # Рекомендации
        report.append("🎯 ПЕРСОНАЛЬНЫЕ РЕКОМЕНДАЦИИ:")
        report.append("-" * 40)
        report.append("✅ Продолжай отслеживать свои показатели ежедневно")
        
        if morning and avg_delta > 20:
            report.append("⚠️ У тебя высокая дельта пульса — нужен отдых и восстановление")
            report.append("   • Отмени HIIT тренировки на 2-3 дня")
            report.append("   • Увеличь время сна на 1 час")
        elif morning and avg_delta > 15:
            report.append("⚠️ Пограничная дельта пульса — снизь интенсивность тренировок")
            report.append("   • Делай легкие тренировки без перегрузок")
            report.append("   • Следи за восстановлением")
        
        if evening and avg_energy < 3:
            report.append("😴 Низкая энергия — проверь качество сна и питание")
            report.append("   • Ложись спать до 23:00")
            report.append("   • Убери сахар и простые углеводы")
            report.append("   • Добавь магний и витамин D")
        
        if evening and hiit_count/len(evening) < 0.5:
            report.append("💪 Старайся выполнять HIIT тренировки регулярно")
            report.append("   • Даже 10 минут HIIT лучше, чем ничего")
            report.append("   • Планируй тренировки заранее")
        
        report.append("")
        report.append("=" * 60)
        report.append("Сгенерировано ботом «Код Реверс»".center(58))
        report.append("=" * 60)
        
        # Записываем в файл
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(report))
        
        return path
    
    # ==================== ЭКСПОРТ В EXCEL ====================
    
    def export_to_excel(self) -> Optional[str]:
        """
        Экспортирует все данные в Excel
        Возвращает путь к временному файлу
        """
        try:
            with sqlite3.connect(DB_NAME) as conn:
                # Загружаем данные в pandas
                morning_df = pd.read_sql_query(
                    "SELECT * FROM morning_checkin WHERE user_id = ? ORDER BY date",
                    conn, params=(self.user_id,)
                )
                
                evening_df = pd.read_sql_query(
                    "SELECT * FROM evening_audit WHERE user_id = ? ORDER BY date",
                    conn, params=(self.user_id,)
                )
                
                weekly_df = pd.read_sql_query(
                    "SELECT * FROM weekly_metrics WHERE user_id = ? ORDER BY date",
                    conn, params=(self.user_id,)
                )
            
            # Создаем Excel файл
            fd, path = tempfile.mkstemp(suffix='.xlsx')
            os.close(fd)
            
            with pd.ExcelWriter(path, engine='openpyxl') as writer:
                if not morning_df.empty:
                    morning_df.to_excel(writer, sheet_name='Утренние замеры', index=False)
                if not evening_df.empty:
                    evening_df.to_excel(writer, sheet_name='Вечерние аудиты', index=False)
                if not weekly_df.empty:
                    weekly_df.to_excel(writer, sheet_name='Недельные замеры', index=False)
                
                # Информация о пользователе
                user_df = pd.DataFrame([self.user_data])
                user_df.to_excel(writer, sheet_name='Профиль', index=False)
            
            return path
            
        except Exception as e:
            print(f"❌ Ошибка создания Excel: {e}")
            return None
    
    # ==================== ТЕКСТОВАЯ АНАЛИТИКА ====================
    
    def get_text_analytics(self) -> str:
        """
        Формирует текстовый отчет с аналитикой
        """
        morning = self.get_morning_data(30)
        evening = self.get_evening_data(30)
        
        text = f"📊 **АНАЛИТИКА ДЛЯ {self.user_data.get('power_name', '')}**\n\n"
        
        if morning:
            # Средние показатели
            avg_sleep = sum(m['sleep_quality'] for m in morning) / len(morning)
            avg_delta = sum(m['pulse_delta'] for m in morning) / len(morning)
            
            text += f"😴 **Сон:** средний {avg_sleep:.1f}/5\n"
            text += f"❤️ **Пульс:** средняя дельта {avg_delta:.1f} уд/мин\n"
            
            # Тренд восстановления
            recent = morning[:7]  # последняя неделя
            old = morning[-7:] if len(morning) >= 14 else morning
            
            if len(recent) >= 7 and len(old) >= 7:
                recent_avg = sum(m['pulse_delta'] for m in recent) / 7
                old_avg = sum(m['pulse_delta'] for m in old) / 7
                
                if recent_avg < old_avg - 2:
                    text += "📈 **Тренд:** ЦНС восстанавливается лучше\n"
                elif recent_avg > old_avg + 2:
                    text += "📉 **Тренд:** ЦНС устает, нужен отдых\n"
        
        if evening:
            # Мотивация и энергия
            avg_motivation = sum(e.get('motivation', 0) for e in evening) / len(evening)
            avg_energy = sum(e.get('energy', 0) for e in evening) / len(evening)
            
            text += f"\n⚡ **Энергия:** средняя {avg_energy:.1f}/5\n"
            text += f"🎯 **Мотивация:** средняя {avg_motivation:.1f}/5\n"
            
            # HIIT
            hiit_count = sum(1 for e in evening if e.get('hiit_done', 0))
            text += f"💪 **HIIT:** выполнено {hiit_count} из {len(evening)} тренировок ({hiit_count/len(evening)*100:.0f}%)\n"
        
        # Рекомендации
        text += "\n🔔 **РЕКОМЕНДАЦИИ:**\n"
        
        if morning and avg_delta > 20:
            text += "• 🚨 Высокая дельта пульса: нужен отдых, отмени HIIT\n"
        elif morning and avg_delta > 15:
            text += "• ⚠️ Пограничная дельта: снизь интенсивность\n"
        
        if evening:
            if avg_motivation < 3:
                text += "• 😴 Низкая мотивация: попробуй сменить активность\n"
            if avg_energy < 3:
                text += "• 🌙 Низкая энергия: проверь сон и питание\n"
        
        return text


# ==================== ХЭНДЛЕРЫ ДЛЯ БОТА ====================

async def show_statistics_menu(message: types.Message):
    """Показать меню статистики"""
    kb = InlineKeyboardBuilder()
    kb.button(text="📈 График пульса", callback_data="stat_pulse")
    kb.button(text="🔄 Фазы цикла", callback_data="stat_cycle")
    kb.button(text="💪 HIIT статистика", callback_data="stat_hiit")
    kb.button(text="⚖️ Динамика веса", callback_data="stat_weight")
    kb.button(text="📊 Полный отчет", callback_data="stat_full")
    kb.button(text="📄 Экспорт в TXT", callback_data="export_txt")
    kb.button(text="📎 Экспорт в Excel", callback_data="export_excel")
    kb.adjust(2)
    
    await message.answer(
        "📊 **Статистика и аналитика**\n\nВыбери, что хочешь посмотреть:",
        reply_markup=kb.as_markup()
    )


async def handle_stat_callback(callback: types.CallbackQuery):
    """Обработка кнопок статистики"""
    stats = StatisticsModule(callback.from_user.id)
    
    if callback.data == "stat_pulse":
        buf = stats.plot_pulse_delta()
        if buf:
            await callback.message.answer_photo(
                types.BufferedInputFile(buf.getvalue(), filename="pulse.png"),
                caption="📈 **Ортопроба** - восстановление ЦНС"
            )
        else:
            await callback.message.answer("❌ Недостаточно данных")
    
    elif callback.data == "stat_cycle":
        buf = stats.plot_cycle_phases()
        if buf:
            await callback.message.answer_photo(
                types.BufferedInputFile(buf.getvalue(), filename="cycle.png"),
                caption="🔄 **Энергия по фазам цикла**"
            )
        else:
            await callback.message.answer("❌ Нет данных о цикле")
    
    elif callback.data == "stat_hiit":
        buf = stats.plot_hiit_compliance()
        if buf:
            await callback.message.answer_photo(
                types.BufferedInputFile(buf.getvalue(), filename="hiit.png"),
                caption="💪 **Выполнение HIIT тренировок**"
            )
        else:
            await callback.message.answer("❌ Недостаточно данных")
    
    elif callback.data == "stat_weight":
        buf = stats.plot_weight_trend()
        if buf:
            await callback.message.answer_photo(
                types.BufferedInputFile(buf.getvalue(), filename="weight.png"),
                caption="⚖️ **Динамика веса**"
            )
        else:
            await callback.message.answer("❌ Недостаточно данных")
    
    elif callback.data == "stat_full":
        text = stats.get_text_analytics()
        await callback.message.answer(text)
    
    elif callback.data == "export_txt":
        await callback.message.answer("📄 Генерирую текстовый отчет...")
        txt_path = stats.generate_txt_report()
        if txt_path:
            with open(txt_path, 'rb') as f:
                await callback.message.answer_document(
                    types.BufferedInputFile(f.read(), filename=f"report_{datetime.now().strftime('%Y%m%d')}.txt"),
                    caption="📊 Твой полный отчет"
                )
            os.unlink(txt_path)
        else:
            await callback.message.answer("❌ Ошибка генерации отчета")
    
    elif callback.data == "export_excel":
        await callback.message.answer("📎 Генерирую Excel файл...")
        excel_path = stats.export_to_excel()
        if excel_path:
            with open(excel_path, 'rb') as f:
                await callback.message.answer_document(
                    types.BufferedInputFile(f.read(), filename=f"data_{datetime.now().strftime('%Y%m%d')}.xlsx"),
                    caption="📊 Все твои данные в Excel"
                )
            os.unlink(excel_path)
        else:
            await callback.message.answer("❌ Ошибка генерации Excel")
    
    await callback.answer()
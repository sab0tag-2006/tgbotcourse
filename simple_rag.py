# simple_rag.py - УЛУЧШЕННАЯ ВЕРСИЯ
"""
Простой поиск по базе знаний для AI-коуча
Читает файл База_знаний.txt и ищет ответы по ключевым словам
"""

import os
import re
from collections import Counter

class SimpleRAG:
    """Просто читает файл База_знаний.txt и ищет ответы"""
    
    def __init__(self, file_path="knowledge_base/База_знаний.txt"):
        self.file_path = file_path
        self.content = ""
        self.lines = []
        self.sections = {}  # Секции по темам
        self.load_file()
        self._build_sections()
    
    def load_file(self):
        """Загружает файл с базой знаний"""
        try:
            if not os.path.exists(self.file_path):
                print(f"❌ Файл {self.file_path} не найден!")
                print("💡 Создай папку 'knowledge_base' и файл 'База_знаний.txt' в ней")
                return
            
            with open(self.file_path, 'r', encoding='utf-8') as f:
                self.content = f.read()
                self.lines = self.content.split('\n')
            print(f"✅ Файл загружен: {len(self.content)} символов, {len(self.lines)} строк")
            
        except Exception as e:
            print(f"❌ Ошибка загрузки файла: {e}")
    
    def _build_sections(self):
        """Разбивает файл на секции по заголовкам"""
        current_section = "Общее"
        current_text = []
        
        for line in self.lines:
            # Ищем заголовки (например, "**ЗАГОЛОВОК**" или "# ЗАГОЛОВОК")
            if line.startswith('**') and line.endswith('**') or line.startswith('# '):
                if current_text:
                    self.sections[current_section] = '\n'.join(current_text)
                current_section = line.strip('*# ')
                current_text = []
            else:
                if line.strip():  # непустые строки
                    current_text.append(line)
        
        # Добавляем последнюю секцию
        if current_text:
            self.sections[current_section] = '\n'.join(current_text)
        
        print(f"✅ Найдено секций: {len(self.sections)}")
    
    def search(self, question, context_lines=20):
        """Ищет ответ в тексте файла"""
        question_lower = question.lower()
        
        # Очищаем вопрос от знаков препинания
        question_clean = re.sub(r'[^\w\s]', ' ', question_lower)
        
        # Ключевые слова из вопроса (исключаем короткие и стоп-слова)
        stop_words = {'что', 'как', 'почему', 'зачем', 'когда', 'где', 'это', 'такое', 
                     'можно', 'нужно', 'стоит', 'есть', 'мой', 'твой', 'наш'}
        
        keywords = [word for word in question_clean.split() 
                   if len(word) > 3 and word not in stop_words]
        
        # Если нет ключевых слов, берем все слова длиннее 2 символов
        if not keywords:
            keywords = [word for word in question_clean.split() if len(word) > 2]
        
        print(f"🔍 Поиск по ключевым словам: {keywords}")
        
        # Собираем совпадения с весами
        matches = []
        match_scores = []
        
        for i, line in enumerate(self.lines):
            line_lower = line.lower()
            score = 0
            
            for keyword in keywords:
                if keyword in line_lower:
                    # Чем больше совпадений в строке, тем выше вес
                    score += line_lower.count(keyword) * 10
                    # Точное совпадение слова дает больший вес
                    if re.search(rf'\b{keyword}\b', line_lower):
                        score += 5
            
            if score > 0:
                # Нашли совпадение, берем контекст вокруг
                start = max(0, i - context_lines // 2)
                end = min(len(self.lines), i + context_lines // 2)
                context = '\n'.join(self.lines[start:end])
                matches.append(context)
                match_scores.append(score)
        
        # Сортируем по релевантности
        sorted_matches = [m for _, m in sorted(zip(match_scores, matches), reverse=True)]
        
        # Убираем дубликаты
        unique_matches = []
        seen = set()
        for match in sorted_matches:
            # Создаем упрощенный ключ для сравнения (первые 100 символов)
            match_key = match[:100]
            if match_key not in seen:
                seen.add(match_key)
                unique_matches.append(match)
        
        return unique_matches[:3]  # Возвращаем топ-3
    
    def search_by_section(self, question):
        """Ищет по секциям (более точный поиск)"""
        question_lower = question.lower()
        
        # Ключевые слова для определения темы
        topic_keywords = {
            'цикл': ['менструация', 'цикл', 'месячные', 'фолликулярная', 'лютеиновая', 'овуляция'],
            'питание': ['еда', 'питание', 'завтрак', 'обед', 'ужин', 'белок', 'жиры', 'углеводы'],
            'тренировки': ['тренировка', 'спорт', 'фитнес', 'hiit', 'нагрузка', 'упражнения'],
            'сон': ['сон', 'спать', 'бессонница', 'просыпаться'],
            'вода': ['вода', 'пить', 'жидкость', 'гидратация'],
            'бады': ['бад', 'витамин', 'минерал', 'добавка', 'магний', 'железо'],
            'генетика': ['ген', 'днк', 'mthfr', 'fto', 'actn3'],
        }
        
        # Определяем наиболее вероятную тему
        topic_scores = {}
        for topic, words in topic_keywords.items():
            score = 0
            for word in words:
                if word in question_lower:
                    score += 1
            if score > 0:
                topic_scores[topic] = score
        
        if topic_scores:
            main_topic = max(topic_scores, key=topic_scores.get)
            print(f"🎯 Определена тема: {main_topic}")
            
            # Ищем в соответствующей секции
            for section_name, section_text in self.sections.items():
                if main_topic in section_name.lower() or any(w in section_name.lower() for w in topic_keywords[main_topic]):
                    return section_text
        
        return None
    
    def answer(self, question):
        """Формирует ответ на вопрос"""
        try:
            # Сначала пробуем найти по секциям
            section_answer = self.search_by_section(question)
            if section_answer and len(section_answer) > 50:
                answer = section_answer
            else:
                # Если не нашли, ищем обычным поиском
                results = self.search(question)
                
                if not results:
                    return self._get_fallback_response(question)
                
                answer = results[0]
            
            # Обрезаем, если слишком длинный
            if len(answer) > 2000:
                answer = answer[:2000] + "..."
            
            return f"📚 **Из базы знаний «Код Реверс»:**\n\n{answer}\n\n💡 *Найдено в файле База_знаний.txt*"
        
        except Exception as e:
            print(f"❌ Ошибка поиска: {e}")
            return f"❌ Ошибка при поиске. Попробуй спросить иначе."
    
    def _get_fallback_response(self, question):
        """Запасные ответы, если ничего не найдено"""
        question_lower = question.lower()
        
        # Проверяем ключевые слова для общих тем
        if any(word in question_lower for word in ['цикл', 'месячные', 'фолликулярная']):
            return ("Похоже, ты спрашиваешь о женском цикле. "
                   "Я могу рассказать о фазах: менструальная (дни 1-5), "
                   "фолликулярная (6-12), овуляция (13-16), лютеиновая (17-24), "
                   "ПМС (25-28). Попробуй спросить конкретнее.")
        
        elif any(word in question_lower for word in ['питание', 'еда', 'завтрак']):
            return ("В системе «Код Реверс» питание зависит от фазы цикла. "
                   "Например, в фолликулярную фазу нужно больше белка, "
                   "в овуляцию — сложные углеводы, в лютеиновую — магний. "
                   "Уточни, какая фаза тебя интересует?")
        
        elif any(word in question_lower for word in ['тренировка', 'hiit', 'спорт']):
            return ("Рекомендации по тренировкам зависят от дня цикла. "
                   "В менструацию и ПМС HIIT запрещен, в овуляцию — пик формы. "
                   "Используй команду /day, чтобы узнать свою нагрузку на сегодня.")
        
        elif any(word in question_lower for word in ['вода', 'пить']):
            return ("Водный баланс критически важен! Норма рассчитывается "
                   "по формуле: вес × 33 мл + коррекция на белок и генетику. "
                   "Используй кнопку '💧 ВОДА' в главном меню.")
        
        else:
            return ("❌ Не нашел точной информации по этому вопросу в базе знаний.\n\n"
                   "Попробуй переформулировать вопрос или спроси о:\n"
                   "• фазах цикла\n"
                   "• питании по дням\n"
                   "• тренировках и HIIT\n"
                   "• водном балансе\n"
                   "• генетике") 
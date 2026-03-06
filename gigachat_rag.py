# gigachat_rag.py - УЛУЧШЕННАЯ ВЕРСИЯ
"""
Модуль для работы с GigaChat API
Использует базу знаний для контекстных ответов
"""

import os
import asyncio
from typing import Optional, Dict, Any, List
from gigachat import GigaChat
from gigachat.models import Chat, Messages, MessagesRole

class GigaChatRAG:
    def __init__(self, auth_key: str, db_path: str = "knowledge_base/База_знаний.txt"):
        """
        Инициализация GigaChat RAG
        
        Args:
            auth_key: Ключ авторизации GigaChat
            db_path: Путь к файлу с базой знаний
        """
        self.auth_key = auth_key
        self.db_path = db_path
        self.client = None
        self.knowledge = ""
        self.knowledge_lines = []
        self._init_client()
        self._load_knowledge()
    
    def _init_client(self):
        """Инициализация клиента GigaChat"""
        try:
            self.client = GigaChat(
                credentials=self.auth_key,
                verify_ssl_certs=False,
                timeout=60,
                model="GigaChat-Pro"
            )
            print("✅ GigaChat клиент инициализирован")
        except Exception as e:
            print(f"❌ Ошибка инициализации GigaChat: {e}")
            self.client = None
    
    def _load_knowledge(self) -> bool:
        """Загружает базу знаний из файла"""
        try:
            if not os.path.exists(self.db_path):
                print(f"❌ Файл не найден: {self.db_path}")
                print("💡 Создай папку 'knowledge_base' и файл 'База_знаний.txt' в ней")
                return False
            
            with open(self.db_path, 'r', encoding='utf-8') as f:
                self.knowledge = f.read()
                self.knowledge_lines = self.knowledge.split('\n')
                
                # Статистика
                chars = len(self.knowledge)
                lines = len(self.knowledge_lines)
                words = len(self.knowledge.split())
                
                print(f"✅ База знаний загружена:")
                print(f"   📁 Файл: {self.db_path}")
                print(f"   📊 Символов: {chars:,}")
                print(f"   📝 Строк: {lines:,}")
                print(f"   🔤 Слов: {words:,}")
                
                # Проверяем наличие ключевых разделов
                sections = []
                for line in self.knowledge_lines[:20]:
                    if line.startswith('**') and line.endswith('**') or line.startswith('# '):
                        sections.append(line.strip('*# '))
                
                if sections:
                    print(f"   📑 Разделы: {', '.join(sections[:5])}")
                
                return True
                
        except Exception as e:
            print(f"❌ Ошибка загрузки базы знаний: {e}")
            return False
    
    def _extract_relevant_context(self, question: str, max_chars: int = 50000) -> str:
        """
        Извлекает релевантный контекст из базы знаний
        
        Args:
            question: Вопрос пользователя
            max_chars: Максимальное количество символов для контекста
        
        Returns:
            Релевантный контекст
        """
        question_lower = question.lower()
        
        # Ключевые слова из вопроса
        keywords = [word for word in question_lower.split() if len(word) > 3]
        
        if not keywords:
            return self.knowledge[:max_chars]
        
        # Ищем строки с ключевыми словами и берем контекст вокруг
        relevant_lines = []
        line_indices = []
        
        for i, line in enumerate(self.knowledge_lines):
            line_lower = line.lower()
            if any(keyword in line_lower for keyword in keywords):
                line_indices.append(i)
        
        # Сортируем и группируем близкие строки
        line_indices.sort()
        context_blocks = []
        current_block = []
        
        for i, idx in enumerate(line_indices):
            if not current_block:
                # Начало блока: берем 5 строк до
                start = max(0, idx - 5)
                current_block = list(range(start, idx))
            
            current_block.append(idx)
            
            # Если следующий индекс далеко или это последний
            if i == len(line_indices) - 1 or line_indices[i + 1] > idx + 10:
                # Добавляем 5 строк после
                end = min(len(self.knowledge_lines), idx + 5)
                current_block.extend(range(idx + 1, end))
                
                # Убираем дубликаты и сортируем
                current_block = sorted(set(current_block))
                
                # Собираем текст блока
                block_text = '\n'.join(self.knowledge_lines[i] for i in current_block)
                context_blocks.append(block_text)
                
                current_block = []
        
        # Объединяем блоки и обрезаем
        context = '\n\n...\n\n'.join(context_blocks)
        
        if len(context) > max_chars:
            context = context[:max_chars] + "..."
        
        print(f"🔍 Найдено {len(line_indices)} релевантных строк, "
              f"сформировано {len(context_blocks)} блоков")
        
        return context if context else self.knowledge[:max_chars]
    
    def _create_prompt(self, question: str, user_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Создает промпт для GigaChat
        
        Args:
            question: Вопрос пользователя
            user_data: Данные пользователя (опционально)
        
        Returns:
            Промпт для отправки в GigaChat
        """
        # Извлекаем релевантный контекст
        context = self._extract_relevant_context(question)
        
        # Добавляем информацию о пользователе, если есть
        user_info = ""
        if user_data:
            user_info = f"""
ДАННЫЕ ПОЛЬЗОВАТЕЛЯ:
- Пол: {"Женщина" if user_data.get('gender_type') == 1 else "Мужчина"}
- Имя силы: {user_data.get('power_name', 'не указано')}
- Тип работы: {user_data.get('work_type', 'не указано')}
- Время пробуждения: {user_data.get('wake_time', 'не указано')}
"""
        
        prompt = f"""Ты - эксперт системы "Код Реверс" по женскому здоровью, циклу, питанию и тренировкам.

ИНСТРУКЦИИ:
1. Используй ТОЛЬКО информацию из базы знаний ниже
2. НЕ ПРИДУМЫВАЙ ничего от себя
3. Если в базе нет ответа - скажи "В базе знаний нет информации по этому вопросу"
4. Отвечай кратко, по делу, дружелюбно
5. Если вопрос не по теме здоровья - вежливо откажись отвечать

{user_info}

БАЗА ЗНАНИЙ:
{context}

ВОПРОС ПОЛЬЗОВАТЕЛЯ: {question}

ОТВЕТ (только по базе, кратко и по делу):"""
        
        return prompt
    
    async def ask(self, question: str, user_data: Optional[Dict[str, Any]] = None) -> str:
        """
        Отправляет вопрос в GigaChat с контекстом из базы знаний
        
        Args:
            question: Вопрос пользователя
            user_data: Данные пользователя (опционально)
        
        Returns:
            Ответ от GigaChat
        """
        # Проверяем, что клиент инициализирован
        if not self.client:
            return "❌ GigaChat не инициализирован. Проверьте настройки."
        
        if not self.knowledge:
            return "❌ База знаний не загружена. Проверьте файл."
        
        try:
            # Проверяем, не спам ли
            if len(question) < 4:
                return "❓ Слишком короткий вопрос. Задай вопрос подробнее."
            
            if len(question) > 1000:
                return "❓ Слишком длинный вопрос. Сократи до 1000 символов."
            
            # Создаем промпт
            prompt = self._create_prompt(question, user_data)
            
            print(f"📤 Отправляю запрос в GigaChat...")
            print(f"   Вопрос: {question[:100]}...")
            print(f"   Контекст: {len(prompt)} символов")
            
            # Отправляем запрос
            response = self.client.chat(prompt)
            
            # Извлекаем ответ
            answer = response.choices[0].message.content
            
            print(f"📥 Получен ответ: {len(answer)} символов")
            
            # Проверяем, не пустой ли ответ
            if not answer or len(answer) < 10:
                return "❌ GigaChat вернул пустой ответ. Попробуй позже."
            
            return answer
            
        except Exception as e:
            error_msg = str(e)
            print(f"❌ Ошибка GigaChat: {error_msg}")
            
            # Обрабатываем специфические ошибки
            if "401" in error_msg:
                return "❌ Ошибка авторизации GigaChat. Проверьте ключ в .env файле."
            elif "429" in error_msg:
                return "❌ Слишком много запросов к GigaChat. Подожди немного."
            elif "timeout" in error_msg.lower():
                return "❌ Таймаут GigaChat. Попробуй позже."
            else:
                return f"❌ Ошибка при обращении к GigaChat. Попробуй позже."
    
    async def ask_with_history(self, question: str, history: List[Dict], user_data: Optional[Dict] = None) -> str:
        """
        Отправляет вопрос с учетом истории диалога
        
        Args:
            question: Вопрос пользователя
            history: История сообщений [{"role": "user/assistant", "content": "..."}]
            user_data: Данные пользователя
        
        Returns:
            Ответ от GigaChat
        """
        if not self.client:
            return "❌ GigaChat не инициализирован."
        
        if not self.knowledge:
            return "❌ База знаний не загружена."
        
        try:
            # Извлекаем контекст
            context = self._extract_relevant_context(question)
            
            # Формируем сообщения для чата
            messages = [
                Messages(
                    role=MessagesRole.SYSTEM,
                    content=f"""Ты - эксперт системы "Код Реверс". 
Используй ТОЛЬКО информацию из базы знаний.
База знаний: {context}"""
                )
            ]
            
            # Добавляем историю (последние 5 сообщений)
            for msg in history[-5:]:
                role = MessagesRole.USER if msg["role"] == "user" else MessagesRole.ASSISTANT
                messages.append(Messages(role=role, content=msg["content"]))
            
            # Добавляем текущий вопрос
            messages.append(Messages(role=MessagesRole.USER, content=question))
            
            # Создаем чат
            chat = Chat(messages=messages)
            
            # Отправляем запрос
            response = self.client.chat(chat)
            
            return response.choices[0].message.content
            
        except Exception as e:
            return f"❌ Ошибка: {e}"
    
    def check_health(self) -> Dict[str, Any]:
        """
        Проверяет состояние модуля
        
        Returns:
            Словарь со статусом
        """
        return {
            "client_ok": self.client is not None,
            "knowledge_loaded": bool(self.knowledge),
            "knowledge_size": len(self.knowledge),
            "knowledge_lines": len(self.knowledge_lines),
            "db_path": self.db_path,
            "file_exists": os.path.exists(self.db_path)
        }
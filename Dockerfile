# Используем официальный образ Python (slim-версия для уменьшения размера)
FROM python:3.11-slim

# Устанавливаем системные зависимости, необходимые для pycairo
# Важно: устанавливаем всё одной командой, чтобы слои были эффективными
RUN apt-get update && apt-get install -y \
    # Базовые утилиты для сборки
    build-essential \
    pkg-config \
    # Библиотеки Cairo и его зависимости
    libcairo2 \
    libcairo2-dev \
    libglib2.0-0 \
    libglib2.0-dev \
    libgirepository1.0-dev \
    libpango1.0-dev \
    libgdk-pixbuf2.0-dev \
    libffi-dev \
    # Дополнительно: часто требуется для работы с графикой
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл с Python-зависимостями
COPY requirements.txt .

# Устанавливаем Python-пакеты
# Флаг --no-cache-dir уменьшает размер образа
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Команда для запуска приложения - ЗАМЕНИТЕ НА ВАШУ!
# Например, если у вас FastAPI: uvicorn main:app --host 0.0.0.0 --port $PORT
# Если Django: gunicorn yourproject.wsgi:application --bind 0.0.0.0:$PORT
# Если простой скрипт: python your_app.py
CMD ["python", "bot.py"]
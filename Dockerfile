# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем системные зависимости, необходимые для pycairo и других библиотек
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libcairo2 \
    libcairo2-dev \
    libpango-1.0-0 \
    libgdk-pixbuf2.0-0 \
    libffi-dev \
    libpangoft2-1.0-0 \
    pkg-config \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл с зависимостями
COPY requirements.txt .

# Устанавливаем Python-зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Указываем команду для запуска приложения (замените на вашу)
bot.py
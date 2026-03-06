# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем системные зависимости для pycairo (исправленная версия)
RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    libcairo2 \
    libcairo2-dev \
    libglib2.0-0 \
    libglib2.0-dev \
    libgirepository1.0-dev \
    libpango1.0-dev \
    libgdk-pixbuf-2.0-dev \
    libffi-dev \
    libjpeg-dev \
    libpng-dev \
    && rm -rf /var/lib/apt/lists/*

# Устанавливаем рабочую директорию
WORKDIR /

# Копируем файл с Python-зависимостями
COPY requirements.txt .

# Устанавливаем Python-пакеты
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальной код приложения
COPY . .

# Эта переменная не обязательна для бота, но Railway её ожидает
ENV PORT=8080

# Запускаем бота
CMD ["python", "bot.py"]
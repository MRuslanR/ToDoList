# Используем официальный образ Python
FROM python:3.9-slim

# Задаём рабочую директорию
WORKDIR /app

# Копируем список зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --upgrade pip && pip install -r requirements.txt

# Копируем весь исходный код в контейнер
COPY . .

# Открываем порт, на котором будет работать Flask
EXPOSE 5000

# Указываем переменную окружения для Flask
ENV FLASK_APP=main.py

# По умолчанию запускаем Flask-сервер
CMD ["flask", "run", "--host=0.0.0.0"]

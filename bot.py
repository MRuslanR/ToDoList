import telebot
from telebot import types
import redis
import json
import requests
import threading
from datetime import datetime
import pytz

import os
from dotenv import load_dotenv
load_dotenv()

TOKEN = os.getenv('TOKEN')

bot = telebot.TeleBot(TOKEN)
r = redis.Redis(host='redis', port=6379, db=0)

def get_auth_inline_keyboard(chat_id):
    auth_url = f"http://127.0.0.1:5001/auto_auth?chat_id={chat_id}"
    markup = types.InlineKeyboardMarkup()
    button = types.InlineKeyboardButton(text="Вход", url=auth_url)
    markup.add(button)
    return markup

def get_main_panel_keyboard():
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    button_login = types.KeyboardButton("Вход")
    button_list = types.KeyboardButton("Список дел")
    button_today = types.KeyboardButton("Список задач на сегодня")
    markup.row(button_login, button_list)
    markup.row(button_today)
    return markup

def redis_listener():
    pubsub = r.pubsub()
    pubsub.subscribe('bot_commands')
    for message in pubsub.listen():
        if message['type'] == 'message':
            try:
                data = json.loads(message['data'])
                chat_id = data['chat_id']
                text = data['message']
                bot.send_message(chat_id, text)
            except Exception as e:
                print(f"Ошибка обработки сообщения из Redis: {e}")

def format_time_diff(deadline_str, target_tz='Europe/Moscow'):
    """
    Преобразует строку с датой (ISO-формат) в сообщение с разницей времени.
    Если дедлайн ещё не наступил, возвращает "осталось HH ч MM м SS с",
    иначе – "просрочено на HH ч MM м SS с".
    """
    try:
        deadline = datetime.fromisoformat(deadline_str)
    except Exception as e:
        return ""
    local_tz = pytz.timezone(target_tz)
    # Если deadline не имеет tzinfo, считаем, что он введён в target_tz
    if deadline.tzinfo is None:
        deadline = local_tz.localize(deadline)
    else:
        deadline = deadline.astimezone(local_tz)
    now = datetime.now(local_tz)
    diff = deadline - now
    total_seconds = diff.total_seconds()
    abs_diff = abs(diff)
    hours = int(abs_diff.total_seconds() // 3600)
    minutes = int((abs_diff.total_seconds() % 3600) // 60)
    seconds = int(abs_diff.total_seconds() % 60)
    time_str = f"{hours} ч {minutes} м {seconds} с"
    if total_seconds > 0:
        return f"осталось {time_str}"
    else:
        return f"просрочено на {time_str}"

@bot.message_handler(commands=['start'])
def send_welcome(message):
    chat_id = str(message.chat.id)
    try:
        response = requests.post(
            'http://web:5000/register',
            json={'chat_id': chat_id},
            timeout=5
        )
        if response.status_code == 201:
            welcome_text = "Регистрация успешна!"
        elif response.status_code == 409:
            welcome_text = "Вы уже зарегистрированы!"
        else:
            bot.reply_to(message, "Ошибка регистрации. Попробуйте позже.")
            return

        # Отправляем сообщение с кнопкой авторизации
        auth_markup = get_auth_inline_keyboard(chat_id)
        bot.send_message(message.chat.id, welcome_text, reply_markup=auth_markup)
        # Отправляем панель с кнопками "Вход", "Список дел" и "Список задач на сегодня"
        panel_markup = get_main_panel_keyboard()
        bot.send_message(message.chat.id, "Выберите действие:", reply_markup=panel_markup)

    except Exception as e:
        print(f"Ошибка: {e}")
        bot.reply_to(message, "Сервис недоступен. Попробуйте позже.")

@bot.message_handler(func=lambda message: message.text.lower() == "вход")
def handle_login(message):
    chat_id = str(message.chat.id)
    auth_markup = get_auth_inline_keyboard(chat_id)
    bot.send_message(message.chat.id, "Для авторизации нажмите кнопку ниже:", reply_markup=auth_markup)

@bot.message_handler(func=lambda message: message.text.lower() == "список дел")
def handle_list_tasks(message):
    chat_id = str(message.chat.id)
    try:
        response = requests.get(
            'http://web:5000/api/tasks',
            params={'chat_id': chat_id},
            timeout=5
        )
        if response.status_code == 200:
            tasks = response.json()
            if tasks:
                message_text = "Ваш список дел 🗒:\n"
                for task in tasks:
                    title = task.get('title', 'Без названия')
                    deadline_str = task.get('deadline', '')
                    time_status = format_time_diff(deadline_str) if deadline_str else ""
                    if not task.get('completed'):
                        message_text += f"{title}: {time_status}\n"
            else:
                message_text = "Список дел пуст."
            if message_text == "Ваш список дел 🗒:\n":
                message_text = "Список дел пуст."
            bot.send_message(message.chat.id, message_text)
        else:
            bot.send_message(message.chat.id, "Не удалось получить список дел. Попробуйте позже.")
    except Exception as e:
        print(f"Ошибка получения списка дел: {e}")
        bot.send_message(message.chat.id, "Сервис недоступен. Попробуйте позже.")

@bot.message_handler(func=lambda message: message.text.lower() == "список задач на сегодня")
def handle_today_tasks(message):
    chat_id = str(message.chat.id)
    try:
        response = requests.get(
            'http://web:5000/api/tasks',
            params={'chat_id': chat_id},
            timeout=5
        )
        if response.status_code == 200:
            tasks = response.json()
            local_tz = pytz.timezone('Europe/Moscow')
            today_date = datetime.now(local_tz).date()
            message_text = "Ваш список задач на сегодня:\n"
            found = False
            for task in tasks:
                deadline_str = task.get('deadline', '')
                if deadline_str:
                    try:
                        deadline = datetime.fromisoformat(deadline_str)
                    except Exception as e:
                        continue
                    # Если deadline не имеет tzinfo, локализуем его
                    if deadline.tzinfo is None:
                        deadline = local_tz.localize(deadline)
                    else:
                        deadline = deadline.astimezone(local_tz)
                    if deadline.date() == today_date and not task.get('completed', False):
                        title = task.get('title', 'Без названия')
                        time_status = format_time_diff(deadline_str)
                        message_text += f"{title}: {time_status}\n"
                        found = True
            if not found:
                message_text = "У вас нет задач на сегодня."
            bot.send_message(message.chat.id, message_text)
        else:
            bot.send_message(message.chat.id, "Не удалось получить список задач. Попробуйте позже.")
    except Exception as e:
        print(f"Ошибка получения списка задач: {e}")
        bot.send_message(message.chat.id, "Сервис недоступен. Попробуйте позже.")

if __name__ == '__main__':
    # Запускаем слушатель Redis в отдельном потоке
    thread = threading.Thread(target=redis_listener)
    thread.daemon = True
    thread.start()

    print("Бот запущен...")
    bot.infinity_polling()

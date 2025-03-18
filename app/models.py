import pymongo
from datetime import datetime
import bcrypt
from bson import ObjectId
from app.celery_worker import celery, schedule_deadline_reminder, schedule_single_reminder, revoke_task
import certifi
import pytz  # для работы с часовыми поясами
from flask import Blueprint, request, jsonify, redirect, url_for
from datetime import timedelta

from flask_login import UserMixin

import os
from dotenv import load_dotenv
load_dotenv()
uri = os.getenv('DATABASE_URI')

client = pymongo.MongoClient(uri, tlsCAFile=certifi.where())
db = client.ToDoList

tasks_bp = Blueprint("tasks", __name__)

def convert_to_utc(time_str, tz_str='Europe/Moscow'):
    dt = datetime.fromisoformat(time_str)
    if dt.tzinfo is None:
        local_tz = pytz.timezone(tz_str)
        dt = local_tz.localize(dt, is_dst=None)
    return dt.astimezone(pytz.utc)


class Task:
    @staticmethod
    def create_task(user_id, title, description, due_date, reminders=None):
        # Сохраняем время, введённое пользователем, без преобразования
        deadline = datetime.fromisoformat(due_date)
        reminders_dt = [datetime.fromisoformat(r) for r in reminders] if reminders else []

        task = {
            "user_id": user_id,
            "title": title,
            "description": description,
            "deadline": deadline,  # сохраняется в локальном времени
            "created_at": datetime.now(),
            "reminders": reminders_dt,  # сохраняются в локальном времени
            "completed": False,
            # Здесь будем хранить id запланированных Celery задач
            "deadline_task_id": None,
            "reminder_task_ids": []
        }
        result = db.tasks.insert_one(task)
        task_id = str(result.inserted_id)

        # Для планирования конвертируем в UTC, но сохраняем исходное время в БД
        utc_deadline = convert_to_utc(due_date)
        if utc_deadline > datetime.now(pytz.utc):
            deadline_task = schedule_deadline_reminder.apply_async(
                eta=utc_deadline,
                args=[user_id, task_id, title]
            )
            db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"deadline_task_id": deadline_task.id}}
            )

        reminder_task_ids = []
        for r in reminders or []:
            utc_reminder = convert_to_utc(r)
            if utc_reminder > datetime.now(pytz.utc):
                reminder_task = schedule_single_reminder.apply_async(
                    eta=utc_reminder,
                    args=[user_id, task_id, title, utc_reminder.isoformat()]
                )
                reminder_task_ids.append(reminder_task.id)
        if reminder_task_ids:
            db.tasks.update_one(
                {"_id": ObjectId(task_id)},
                {"$set": {"reminder_task_ids": reminder_task_ids}}
            )


    @staticmethod
    def update_task(task_id, title, description, deadline, reminders):
        # Вспомогательная функция:
        # Если строка заканчивается на 'Z', заменяем её на '+00:00' для корректного парсинга,
        # затем прибавляем 3 часа к полученному времени.
        def parse_iso_and_add3(dt_str):
            if dt_str.endswith('Z'):
                dt_str = dt_str.replace('Z', '+00:00')
            return datetime.fromisoformat(dt_str) + timedelta(hours=3)

        # Получаем старую задачу
        old_task = Task.get_task_by_id(task_id)
        # Отменяем ранее запланированные задачи, если они есть
        if old_task.get("deadline_task_id"):
            revoke_task(old_task["deadline_task_id"])
        for rem_id in old_task.get("reminder_task_ids", []):
            revoke_task(rem_id)

        # Парсим дату дедлайна и напоминания с прибавлением 3 часов
        new_deadline = parse_iso_and_add3(deadline)
        reminders_dt = [parse_iso_and_add3(r) for r in reminders] if reminders else []

        update_data = {
            "title": title,
            "description": description,
            "deadline": new_deadline,  # сохраняем время с прибавленными 3 часами
            "reminders": reminders_dt,
            "deadline_task_id": None,
            "reminder_task_ids": []
        }
        db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": update_data})

        # Планируем новые задачи, переводя обновлённое время (с поправкой) в UTC
        task = Task.get_task_by_id(task_id)
        if not task["completed"]:
            utc_deadline = convert_to_utc(new_deadline.replace(tzinfo=None).isoformat())
            if utc_deadline > datetime.now(pytz.utc):
                deadline_task = schedule_deadline_reminder.apply_async(
                    eta=utc_deadline,
                    args=[task["user_id"], task_id, title]
                )
                db.tasks.update_one(
                    {"_id": ObjectId(task_id)},
                    {"$set": {"deadline_task_id": deadline_task.id}}
                )
            reminder_task_ids = []
            for r in reminders_dt:
                utc_reminder = convert_to_utc(r.replace(tzinfo=None).isoformat())
                if utc_reminder > datetime.now(pytz.utc):
                    reminder_task = schedule_single_reminder.apply_async(
                        eta=utc_reminder,
                        args=[task["user_id"], task_id, title, utc_reminder.isoformat()]
                    )
                    reminder_task_ids.append(reminder_task.id)
            if reminder_task_ids:
                db.tasks.update_one(
                    {"_id": ObjectId(task_id)},
                    {"$set": {"reminder_task_ids": reminder_task_ids}}
                )

    @staticmethod
    def update_task_status(task_id, completed):
        task = Task.get_task_by_id(task_id)
        if completed and task:
            if task.get("deadline_task_id"):
                revoke_task(task["deadline_task_id"])
            for rem_id in task.get("reminder_task_ids", []):
                revoke_task(rem_id)
        else:
            Task.update_task(
                task_id,
                task["title"],
                task["description"],
                task["deadline"].isoformat(),
                [dt.isoformat() for dt in task.get("reminders", [])]
            )
        db.tasks.update_one({"_id": ObjectId(task_id)}, {"$set": {"completed": completed}})

    @staticmethod
    def get_user_tasks(user_id):
        return list(db.tasks.find({"user_id": user_id}))

    @staticmethod
    def get_task_by_id(task_id):
        return db.tasks.find_one({"_id": ObjectId(task_id)})

    @staticmethod
    def delete_task(task_id):
        task = Task.get_task_by_id(task_id)
        if task:
            if task.get("deadline_task_id"):
                revoke_task(task["deadline_task_id"])
            for rem_id in task.get("reminder_task_ids", []):
                revoke_task(rem_id)
        db.tasks.delete_one({"_id": ObjectId(task_id)})

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data

    @property
    def id(self):
        return str(self.user_data['chat_id'])

    @staticmethod
    def user_exists(chat_id):
        return db.users.find_one({"chat_id": chat_id})

    @staticmethod
    def get_by_chat_id(chat_id):
        user_data = db.users.find_one({"chat_id": chat_id})
        return User(user_data) if user_data else None

    @staticmethod
    def register_user(chat_id):
        try:
            db.users.insert_one({
                "chat_id": chat_id,
                "created_at": datetime.now()
            })
            return True
        except Exception as e:
            print("Ошибка регистрации:", e)
            return False

from app import login_manager
@login_manager.user_loader
def load_user(user_id):
    return User.get_by_chat_id(user_id)

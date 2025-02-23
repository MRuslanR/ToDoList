import pymongo
from datetime import datetime
import bcrypt
from bson import ObjectId

from flask_login import UserMixin


client = pymongo.MongoClient("mongodb://localhost:27017")
db = client.ToDoList

class Task:
    @staticmethod
    def create_task(user_id, title, description, due_date, reminders=None):
        deadline = datetime.fromisoformat(due_date)
        task = {
            "user_id": ObjectId(user_id),
            "title": title,
            "description": description,
            "deadline": deadline,
            "created_at": datetime.now(),
            "reminders": reminders or [],
            "completed": False
        }
        db.tasks.insert_one(task)

    @staticmethod
    def get_user_tasks(user_id):
        return list(db.tasks.find({"user_id": ObjectId(user_id)}))

    @staticmethod
    def get_task_by_id(task_id):
        return db.tasks.find_one({"_id": ObjectId(task_id)})

    @staticmethod
    def update_task(task_id, title, description, deadline, reminders):
        db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {
                "title": title,
                "description": description,
                "deadline": datetime.fromisoformat(deadline),
                "reminders": reminders
            }}
        )

    @staticmethod
    def update_task_status(task_id, completed):
        db.tasks.update_one(
            {"_id": ObjectId(task_id)},
            {"$set": {"completed": completed}}
        )

    @staticmethod
    def delete_task(task_id):
        db.tasks.delete_one({"_id": ObjectId(task_id)})

class User(UserMixin):
    def __init__(self, user_data):
        self.user_data = user_data

    @property
    def id(self):
        return str(self.user_data['_id'])

    @staticmethod
    def user_exists(username):
        return db.users.find_one({"username": username})

    @staticmethod
    def get_by_id(user_id):
        user_data = db.users.find_one({"_id": ObjectId(user_id)})
        return User(user_data) if user_data else None


    @staticmethod
    def register_user(username, email, password):
        try:
            db.users.insert_one({
                "username": username,
                "email": email,
                "password": bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()),
                "created_at": datetime.now()
            })
            return True
        except:
            return False

    @staticmethod
    def authenticate_user(username, password):
        user_data = db.users.find_one({"username": username})
        if user_data and bcrypt.checkpw(password.encode('utf-8'), user_data['password']):
            return User(user_data)
        return None


from app import login_manager
@login_manager.user_loader
def load_user(user_id):
    return User.get_by_id(user_id)
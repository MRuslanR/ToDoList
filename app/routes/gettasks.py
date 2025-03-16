from flask import Blueprint, request, jsonify
from app.models import Task, User
from datetime import datetime
import pytz

get_tasks_bp = Blueprint("get_tasks", __name__)


@get_tasks_bp.route('/api/tasks', methods=['GET'])
def api_get_tasks():
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return jsonify({"error": "Chat ID required"}), 400

    # Получаем пользователя по chat_id
    user = User.get_by_chat_id(chat_id)
    if not user:
        return jsonify({"error": "User not found"}), 404

    tasks = Task.get_user_tasks(user.id)
    # Сортируем задачи по дедлайну
    tasks.sort(key=lambda x: x['deadline'])

    # Приводим данные к формату, пригодному для JSON (например, преобразуем datetime в ISO)
    for t in tasks:
        t['_id'] = str(t['_id'])
        t['user_id'] = str(t['user_id'])
        if isinstance(t.get('deadline'), datetime):
            t['deadline'] = t['deadline'].isoformat()
        if isinstance(t.get('created_at'), datetime):
            t['created_at'] = t['created_at'].isoformat()
        if t.get('reminders'):
            t['reminders'] = [r.isoformat() if isinstance(r, datetime) else r for r in t['reminders']]

    return jsonify(tasks)

from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user

from ..models import Task


tasks_bp = Blueprint("tasks", __name__)


def check_task_ownership(task_id):
    """Проверяет принадлежность задачи текущему пользователю"""
    task = Task.get_task_by_id(task_id)
    if not task:
        return None
    if str(task['user_id']) != current_user.id:
        return None
    return task


@tasks_bp.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        deadline = request.form.get('deadline')
        reminders = request.form.getlist('reminders')

        Task.create_task(
            user_id=current_user.id,
            title=title,
            description=description,
            due_date=deadline,
            #reminders=reminders
        )
        return redirect(url_for('tasks.tasks'))

    tasks = Task.get_user_tasks(current_user.id)
    active_tasks = [t for t in tasks if not t["completed"]]
    completed_tasks = [t for t in tasks if t["completed"]]
    return render_template("tasks.html",
                           active_tasks=active_tasks,
                           completed_tasks=completed_tasks)

@tasks_bp.route('/task/<task_id>', methods=['PUT'])
def update_task(task_id):
    data = request.json
    Task.update_task(
        task_id,
        data.get('title'),
        data.get('description'),
        data.get('deadline'),
        data.get('reminders', [])
    )
    return jsonify({'status': 'success'})

@tasks_bp.route('/task/<task_id>', methods=['GET'])
def get_task(task_id):
    task = Task.get_task_by_id(task_id)
    if task:
        # Конвертируем ObjectId в строку для JSON
        task['_id'] = str(task['_id'])
        return jsonify(task)
    return jsonify({'error': 'Task not found'}), 404


@tasks_bp.route('/task/<task_id>/status', methods=['PUT'])
def update_task_status(task_id):
    data = request.json
    Task.update_task_status(
        task_id,
        data.get('completed', False)
    )
    return jsonify({'status': 'success'})

@tasks_bp.route('/task/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    Task.delete_task(task_id)
    return jsonify({'status': 'success'})


@tasks_bp.route('/task')
def task():
    return render_template("task.html")

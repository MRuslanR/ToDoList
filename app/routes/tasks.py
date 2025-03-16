from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user
from ..models import Task

tasks_bp = Blueprint("tasks", __name__)


def check_task_ownership(task_id):
    try:
        task = Task.get_task_by_id(task_id)
        if not task or str(task['user_id']) != current_user.id:
            return None
        return task
    except Exception as e:
        print(f"Ошибка проверки прав: {e}")
        return None

@tasks_bp.route('/tasks', methods=['GET', 'POST'])
@login_required
def tasks():
    if request.method == 'POST':
        Task.create_task(
            user_id=current_user.id,
            title=request.form.get('title'),
            description=request.form.get('description'),
            due_date=request.form.get('deadline'),
            reminders=request.form.getlist('reminders')
        )
        return redirect(url_for('tasks.tasks'))

    tasks = Task.get_user_tasks(current_user.id)
    return render_template("tasks.html",
                           active_tasks=[t for t in tasks if not t["completed"]],
                           completed_tasks=[t for t in tasks if t["completed"]])


@tasks_bp.route('/task/<task_id>', methods=['PUT'])
@login_required
def update_task(task_id):
    if not check_task_ownership(task_id):
        return jsonify({'error': 'Access denied'}), 403
    data = request.json
    Task.update_task(
        task_id=task_id,
        title=data.get('title'),
        description=data.get('description'),
        deadline=data.get('deadline'),
        reminders=data.get('reminders', [])
    )
    return jsonify({'status': 'success'})


@tasks_bp.route('/task/<task_id>', methods=['GET'])
@login_required
def get_task(task_id):
    task = check_task_ownership(task_id)
    if not task:
        return jsonify({'error': 'Task not found'}), 404

    task['_id'] = str(task['_id'])
    task['user_id'] = str(task['user_id'])
    return jsonify(task)


@tasks_bp.route('/task/<task_id>/status', methods=['PUT'])
@login_required
def update_task_status(task_id):
    task = check_task_ownership(task_id)
    if not task:
        return jsonify({'error': 'Access denied'}), 403

    try:
        completed = request.json.get('completed', False)
        Task.update_task_status(
            task_id=task_id,
            completed=completed
        )
        return jsonify({'status': 'success'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@tasks_bp.route('/task/<task_id>', methods=['DELETE'])
@login_required
def delete_task(task_id):
    if not check_task_ownership(task_id):
        return jsonify({'error': 'Access denied'}), 403

    Task.delete_task(task_id)
    return jsonify({'status': 'success'})
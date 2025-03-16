from flask import Blueprint, request, redirect, url_for, jsonify, render_template_string
from flask_login import login_required, logout_user, login_user
from app.models import User

authorization_bp = Blueprint("authorization", __name__)


@authorization_bp.route('/login', methods=['GET', 'POST'])
def login():
    """
    Отображает форму для ввода chat_id и обрабатывает авторизацию.
    Если авторизация успешна, перенаправляет пользователя на параметр next или на /tasks.
    """
    if request.method == 'POST':
        chat_id = request.form.get('chat_id')
        if not chat_id:
            return "Chat ID не указан", 400

        user = User.get_by_chat_id(chat_id)
        if not user:
            return "Пользователь не найден", 404

        login_user(user)
        next_page = request.args.get('next') or url_for("tasks.tasks")
        return redirect(next_page)

    # Простейшая форма для авторизации
    form_html = """
    <form method="post">
        <label>Введите Chat ID:</label>
        <input type="text" name="chat_id" required>
        <button type="submit">Войти</button>
    </form>
    """
    return render_template_string(form_html)


@authorization_bp.route('/auto_auth', methods=['GET'])
def auto_auth():
    """Endpoint для авторизации через ссылку из бота (автоматическая авторизация)"""
    chat_id = request.args.get('chat_id')
    if not chat_id:
        return "Chat ID не указан", 400

    user = User.get_by_chat_id(chat_id)
    if not user:
        return "Пользователь не найден", 404

    login_user(user)
    return redirect(url_for("tasks.tasks"))


@authorization_bp.route('/register', methods=['POST'])
def register():
    """Новый endpoint для регистрации"""
    chat_id = request.json.get('chat_id')
    if not chat_id:
        return jsonify({"error": "Chat ID required"}), 400

    if User.user_exists(chat_id):
        return jsonify({"error": "User already exists"}), 409

    if User.register_user(chat_id):
        return jsonify({"message": "User registered successfully"}), 201
    else:
        return jsonify({"error": "Registration failed"}), 500


@authorization_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("index.index"))
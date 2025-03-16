from flask import Flask, request, redirect, url_for
from flask_login import LoginManager, login_user
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'the random string'
app.config.update(
    CELERY_BROKER_URL='redis://redis:6379/0',
    CELERY_RESULT_BACKEND='redis://redis:6379/0',
    CELERY_ACCEPT_CONTENT=['json'],
    CELERY_TASK_SERIALIZER='json'
)

# Инициализация Flask-Login
login_manager = LoginManager(app)
login_manager.login_view = 'authorization.login'

# Импорт моделей после создания login_manager для предотвращения циклических импортов
from app.models import User, Task

@login_manager.user_loader
def load_user(user_id):
    return User.get_by_chat_id(user_id)

# Регистрация blueprint-ов
from app.routes.authorization import authorization_bp
from app.routes.tasks import tasks_bp
from app.routes.index import index_bp
from app.routes.gettasks import get_tasks_bp

app.register_blueprint(get_tasks_bp)
app.register_blueprint(authorization_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(index_bp)

# Фильтр для форматирования дат в шаблонах
@app.template_filter('datetime_format')
def datetime_format(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%d %b %Y, %H:%M")

# Контекстный процессор для передачи текущей даты и времени в шаблоны
@app.context_processor
def inject_now():
    return {'now': datetime.now()}

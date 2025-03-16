from celery import Celery
from app import app
import redis
import json
from datetime import datetime, timedelta

# Инициализация подключения к Redis
r = redis.Redis(host='redis', port=6379, db=0)

def make_celery(app):
    celery = Celery(
        app.import_name,
        broker=app.config['CELERY_BROKER_URL'],
        backend=app.config['CELERY_RESULT_BACKEND']
    )
    celery.conf.update(app.config)
    class ContextTask(celery.Task):
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return super().__call__(*args, **kwargs)
    celery.Task = ContextTask
    return celery

celery = make_celery(app)

def revoke_task(task_id):
    try:
        celery.control.revoke(task_id, terminate=True)
        print(f"Отменена задача Celery с id: {task_id}")
    except Exception as e:
        print(f"Ошибка отмены задачи {task_id}: {e}")

@celery.task(name='schedule_deadline_reminder')
def schedule_deadline_reminder(chat_id, task_id, task_title):
    """
    Задача отправляет уведомление о том, что дедлайн задачи подошел к концу.
    После этого планируется дополнительная задача, которая через заданную задержку (1 минута для отладки,
    в продакшене – 1 день) уведомит пользователя, что задача вычеркнута, и изменит её статус.
    """
    from app.models import Task  # Импорт здесь для избежания циклических импортов
    task = Task.get_task_by_id(task_id)
    if task and not task.get("completed"):
        send_to_bot(chat_id, f"Дедлайн задачи {task_title} подошел к концу 💀. Задача будет продлена на 1 день, после чего - вычеркнута.")
        print(f"Напоминание для дедлайна задачи {task_id} отправлено")
        # Планируем finalize_task через 1 минуту (для отладки, вместо 1 дня)
        finalize_eta = datetime.utcnow() + timedelta(days=1)
        finalize_task.apply_async(eta=finalize_eta, args=[chat_id, task_id, task_title])
    else:
        print(f"Задача {task_id} выполнена или удалена. Напоминание не отправлено.")

@celery.task(name='schedule_single_reminder')
def schedule_single_reminder(chat_id, task_id, task_title, reminder_time):
    """
    Задача отправляет напоминание, если задача не выполнена.
    Параметр reminder_time должен быть в UTC.
    """
    from app.models import Task
    task = Task.get_task_by_id(task_id)
    if task and not task.get("completed"):
        send_to_bot(chat_id, f"Напоминание для задачи {task_title} 🔔")
        print(f"Напоминание для задачи {task_id} на {reminder_time} отправлено")
    else:
        print(f"Задача {task_id} выполнена или удалена. Напоминание не отправлено.")

@celery.task(name='finalize_task')
def finalize_task(chat_id, task_id, task_title):
    """
    Эта задача срабатывает по истечении задержки после дедлайна.
    Она уведомляет пользователя о том, что задача вычеркнута, и обновляет её статус.
    """
    from app.models import Task
    # Изменяем статус задачи на завершённый (вычеркнутую)
    Task.update_task_status(task_id, True)
    send_to_bot(chat_id, f"Задача {task_title} вычеркнута, так как дедлайн истек ✏️")
    print(f"Задача {task_id} завершена и вычеркнута.")

def send_to_bot(chat_id, message):
    try:
        payload = json.dumps({
            'chat_id': chat_id,
            'message': message
        })
        r.publish('bot_commands', payload)
    except Exception as e:
        print(f"Ошибка отправки напоминания: {e}")

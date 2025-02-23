from flask import Flask
from flask_login import LoginManager


app = Flask(__name__, template_folder='templates', static_folder='static')
app.config['SECRET_KEY'] = 'the random string'

login_manager = LoginManager(app)


from .routes.authorization import authorization_bp
from .routes.tasks import tasks_bp
from .routes.index import index_bp

app.register_blueprint(authorization_bp)
app.register_blueprint(tasks_bp)
app.register_blueprint(index_bp)


from datetime import datetime
@app.template_filter('datetime_format')
def datetime_format(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime("%d %b %Y, %H:%M")

@app.context_processor
def inject_now():
    return {'now': datetime.now()}
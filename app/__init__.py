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

'''
from datetime import datetime
@app.template_filter('datetimeformat')
def datetimeformat(value, format='%Y-%m-%d %H:%M'):
    if isinstance(value, str):
        value = datetime.fromisoformat(value)
    return value.strftime(format)
'''

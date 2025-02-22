from flask import Blueprint, render_template, request, redirect, url_for, session
from flask_login import login_required, logout_user, login_user

from ..models import User

authorization_bp = Blueprint("authorization", __name__)

@authorization_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.authenticate_user(username, password)
        if not user:
            return render_template("login.html", error="Invalid username or password")

        login_user(user)
        return redirect(url_for('tasks.tasks'))

    return render_template("login.html")


@authorization_bp.route('/register', methods=['GET', 'POST'])
def register():
    error = None
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            error = "Passwords don't match"
        elif User.user_exists(username):
            error = "Username already exists"
        else:
            if User.register_user(username, email, password):
                return redirect(url_for('authorization.login'))
            else:
                error = "Registration failed"

    return render_template("register.html", error=error)


@authorization_bp.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for("index.index"))
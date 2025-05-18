from flask import Blueprint, render_template, request, redirect, url_for, session, flash
from werkzeug.security import check_password_hash
from app import mysql

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        cursor.close()

        if user and check_password_hash(user['password_hash'], password):
            session['user_id'] = user['id']
            session['role'] = user['role']
            session['lang'] = user.get('preferred_lang', 'cz')
            flash("Login successful.", "success")
            return redirect(url_for('driver.dashboard') if user['role'] == 'driver' else url_for('employee.dashboard'))
        else:
            flash("Invalid email or password.", "danger")

    return render_template('auth/login.html')


@auth_bp.route('/logout')
def logout():
    session.clear()
    flash("Logged out.", "info")
    return redirect(url_for('auth.login'))

from flask import Blueprint, render_template, session, redirect, url_for

manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

@manager_bp.route('/dashboard')
def dashboard():
    if session.get('role') != 'manager':
        return redirect(url_for('auth.login'))
    return render_template('manager/dashboard.html')

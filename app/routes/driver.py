from flask import Blueprint, render_template, session, redirect, url_for
from app.models.deliveries import get_deliveries_by_driver, update_delivery_status
from datetime import date

driver_bp = Blueprint('driver', __name__, url_prefix='/driver')

@driver_bp.route('/dashboard')
def dashboard():
    if session.get('role') != 'driver':
        return redirect(url_for('auth.login'))

    deliveries = get_deliveries_by_driver(session['user_id'], date.today())
    return render_template('driver/dashboard.html', deliveries=deliveries)

@driver_bp.route('/delivery/<int:delivery_id>/accept')
def accept_delivery(delivery_id):
    if session.get('role') != 'driver':
        return redirect(url_for('auth.login'))
    update_delivery_status(delivery_id, 'accepted')
    return redirect(url_for('driver.dashboard'))

@driver_bp.route('/delivery/<int:delivery_id>/reject')
def reject_delivery(delivery_id):
    if session.get('role') != 'driver':
        return redirect(url_for('auth.login'))
    update_delivery_status(delivery_id, 'rejected')
    return redirect(url_for('driver.dashboard'))

@driver_bp.route('/delivery/<int:delivery_id>/complete')
def complete_delivery(delivery_id):
    if session.get('role') != 'driver':
        return redirect(url_for('auth.login'))
    update_delivery_status(delivery_id, 'completed')
    return redirect(url_for('driver.dashboard'))

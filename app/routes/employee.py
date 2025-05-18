from flask import Blueprint, render_template, session, redirect, url_for, request
from datetime import datetime, date, timedelta

from app.models.addresses import get_all_addresses, create_address
from app.models.users import get_all_drivers
from app.models.deliveries import (
    create_delivery,
    get_all_deliveries_grouped,
    delete_delivery
)
from app import mysql

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/dashboard')
def dashboard():
    if session.get('role') != 'employee':
        return redirect(url_for('auth.login'))

    cursor = mysql.connection.cursor()

    # Delivery count for today
    cursor.execute("SELECT COUNT(*) as count FROM deliveries WHERE delivery_date = %s", (date.today(),))
    today_count = cursor.fetchone()['count']

    # Delivery count for current week
    start = date.today()
    end = start + timedelta(days=6)
    cursor.execute("SELECT COUNT(*) as count FROM deliveries WHERE delivery_date BETWEEN %s AND %s", (start, end))
    week_count = cursor.fetchone()['count']

    # Next upcoming delivery
    cursor.execute("""
        SELECT d.delivery_date, a.label
        FROM deliveries d
        JOIN addresses a ON d.address_id = a.id
        WHERE d.delivery_date >= %s
        ORDER BY d.delivery_date ASC
        LIMIT 1
    """, (date.today(),))
    next_delivery = cursor.fetchone()

    cursor.close()

    return render_template('employee/dashboard.html',
                           today_count=today_count,
                           week_count=week_count,
                           next_delivery=next_delivery)

@employee_bp.route('/addresses', methods=['GET', 'POST'])
def addresses():
    if session.get('role') not in ['employee', 'manager']:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        label = request.form['label']
        street = request.form['street']
        city = request.form['city']
        zip_code = request.form['zip']
        lat = request.form['latitude']
        lon = request.form['longitude']
        user_id = session['user_id']
        create_address(label, street, city, zip_code, lat, lon, user_id)
        return redirect(url_for('employee.addresses'))

    addresses = get_all_addresses()
    return render_template('employee/addresses.html', addresses=addresses)

@employee_bp.route('/schedule', methods=['GET', 'POST'])
def schedule():
    if session.get('role') not in ['employee', 'manager']:
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        driver_id = request.form['driver_id']
        address_id = request.form['address_id']
        date = request.form['delivery_date']
        start = request.form['start_time']
        end = request.form['end_time']
        notes = request.form['notes']
        assigned_by = session['user_id']

        create_delivery(driver_id, address_id, date, start, end, assigned_by, notes)
        return redirect(url_for('employee.schedule'))

    drivers = get_all_drivers()
    addresses = get_all_addresses()
    return render_template('employee/schedule.html', drivers=drivers, addresses=addresses)

@employee_bp.route('/calendar', methods=['GET', 'POST'])
def calendar():
    if session.get('role') not in ['employee', 'manager']:
        return redirect(url_for('auth.login'))

    filter_driver = request.args.get('driver')
    filter_date = request.args.get('date')
    schedule = get_all_deliveries_grouped(filter_driver, filter_date)
    return render_template('employee/calendar.html', schedule=schedule)

@employee_bp.route('/delivery/<int:delivery_id>/delete')
def delete_delivery_route(delivery_id):
    if session.get('role') not in ['employee', 'manager']:
        return redirect(url_for('auth.login'))
    delete_delivery(delivery_id)
    return redirect(url_for('employee.calendar'))

@employee_bp.route('/delivery/<int:delivery_id>/edit', methods=['GET', 'POST'])
def edit_delivery(delivery_id):
    if session.get('role') not in ['employee', 'manager']:
        return redirect(url_for('auth.login'))

    cursor = mysql.connection.cursor()

    if request.method == 'POST':
        driver_id = request.form['driver_id']
        address_id = request.form['address_id']
        date = request.form['delivery_date']
        start = request.form['start_time']
        end = request.form['end_time']
        notes = request.form['notes']

        cursor.execute("""
            UPDATE deliveries
            SET driver_id=%s, address_id=%s, delivery_date=%s,
                start_time=%s, end_time=%s, notes=%s
            WHERE id=%s
        """, (driver_id, address_id, date, start, end, notes, delivery_id))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('employee.calendar'))

    cursor.execute("SELECT * FROM deliveries WHERE id = %s", (delivery_id,))
    delivery = cursor.fetchone()
    cursor.close()

    drivers = get_all_drivers()
    addresses = get_all_addresses()

    return render_template('employee/edit_delivery.html',
                           delivery=delivery,
                           drivers=drivers,
                           addresses=addresses)

from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, current_app
from flask_babel import _
from datetime import datetime, date, timedelta
from typing import Dict, Any
import logging

from app.models.addresses import get_all_addresses, create_address, get_address_by_id
from app.models.users import get_all_drivers, get_user_by_id
from app.services.delivery_service import DeliveryService
from app.middleware import login_required, role_required, rate_limit_by_ip
from app.utils import validate_email, sanitize_input, format_datetime
from app import mysql

logger = logging.getLogger(__name__)

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/dashboard')
@login_required
@role_required('employee', 'manager')
def dashboard():
    try:
        # Get delivery statistics
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        
        stats = DeliveryService.get_delivery_stats(
            week_start.isoformat(),
            week_end.isoformat()
        )

        # Get next upcoming delivery
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                d.id,
                d.delivery_date,
                d.start_time,
                a.label,
                u.name as driver_name
            FROM deliveries d
            JOIN addresses a ON d.address_id = a.id
            JOIN users u ON d.driver_id = u.id
            WHERE d.delivery_date >= %s
            AND d.status = 'pending'
            ORDER BY d.delivery_date ASC, d.start_time ASC
            LIMIT 1
        """, (today.isoformat(),))
        next_delivery = cursor.fetchone()
        cursor.close()

        if next_delivery:
            next_delivery['delivery_date'] = format_datetime(next_delivery['delivery_date'])
            next_delivery['start_time'] = format_datetime(next_delivery['start_time'])

        return render_template('employee/dashboard.html',
                             stats=stats,
                             next_delivery=next_delivery)
    except Exception as e:
        flash(_("Error loading dashboard data"), "danger")
        return render_template('employee/dashboard.html')

@employee_bp.route('/addresses', methods=['GET', 'POST'])
@login_required
@role_required('employee', 'manager')
def addresses():
    if request.method == 'POST':
        try:
            # Validate and sanitize input
            label = sanitize_input(request.form.get('label', ''))
            street = sanitize_input(request.form.get('street', ''))
            city = sanitize_input(request.form.get('city', ''))
            zip_code = sanitize_input(request.form.get('zip', ''))
            
            try:
                lat = float(request.form.get('latitude', 0))
                lon = float(request.form.get('longitude', 0))
            except ValueError:
                flash(_("Invalid coordinates"), "danger")
                return redirect(url_for('employee.addresses'))

            if not all([label, street, city, zip_code]):
                flash(_("All fields are required"), "danger")
                return redirect(url_for('employee.addresses'))

            # Create address
            address_id = create_address(
                label=label,
                street=street,
                city=city,
                zip_code=zip_code,
                lat=lat,
                lon=lon,
                user_id=session['user_id']
            )

            if address_id:
                flash(_("Address added successfully"), "success")
            else:
                flash(_("Error adding address"), "danger")
        except Exception as e:
            flash(_("Error processing address"), "danger")
        return redirect(url_for('employee.addresses'))

    addresses = get_all_addresses()
    return render_template('employee/addresses.html', addresses=addresses)

@employee_bp.route('/schedule', methods=['GET', 'POST'])
@login_required
@role_required('employee', 'manager')
@rate_limit_by_ip("30 per minute")
def schedule():
    if request.method == 'POST':
        try:
            # Validate input
            driver_id = request.form.get('driver_id')
            address_id = request.form.get('address_id')
            delivery_date = request.form.get('delivery_date')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            notes = sanitize_input(request.form.get('notes', ''))

            if not all([driver_id, address_id, delivery_date, start_time, end_time]):
                flash(_("All fields are required"), "danger")
                return redirect(url_for('employee.schedule'))

            # Validate driver and address exist
            driver = get_user_by_id(driver_id)
            address = get_address_by_id(address_id)
            
            if not driver or not address:
                flash(_("Invalid driver or address"), "danger")
                return redirect(url_for('employee.schedule'))

            # Create delivery
            delivery_id = DeliveryService.create_delivery(
                driver_id=int(driver_id),
                address_id=int(address_id),
                date=delivery_date,
                start_time=start_time,
                end_time=end_time,
                assigned_by=session['user_id'],
                notes=notes
            )

            if delivery_id:
                flash(_("Delivery scheduled successfully"), "success")
            else:
                flash(_("Error scheduling delivery"), "danger")
        except Exception as e:
            flash(_("Error processing delivery schedule"), "danger")
        return redirect(url_for('employee.schedule'))

    drivers = get_all_drivers()
    addresses = get_all_addresses()
    return render_template('employee/schedule.html',
                         drivers=drivers,
                         addresses=addresses)

@employee_bp.route('/calendar')
@login_required
@role_required('employee', 'manager')
def calendar():
    try:
        filter_driver = request.args.get('driver')
        filter_date = request.args.get('date')
        
        # Validate date format if provided
        if filter_date:
            try:
                datetime.strptime(filter_date, '%Y-%m-%d')
            except ValueError:
                filter_date = None
                flash(_("Invalid date format"), "warning")

        schedule = DeliveryService.get_all_deliveries_grouped(filter_driver, filter_date)
        return render_template('employee/calendar.html', schedule=schedule)
    except Exception as e:
        flash(_("Error loading calendar"), "danger")
        return render_template('employee/calendar.html', schedule={})

@employee_bp.route('/delivery/<int:delivery_id>/delete', methods=['POST'])
@login_required
@role_required('employee', 'manager')
def delete_delivery_route(delivery_id):
    try:
        if DeliveryService.delete_delivery(delivery_id):
            flash(_("Delivery deleted successfully"), "success")
        else:
            flash(_("Error deleting delivery"), "danger")
    except Exception as e:
        flash(_("Error processing deletion"), "danger")
    return redirect(url_for('employee.calendar'))

@employee_bp.route('/delivery/<int:delivery_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('employee', 'manager')
def edit_delivery(delivery_id):
    try:
        if request.method == 'POST':
            # Validate input
            driver_id = request.form.get('driver_id')
            address_id = request.form.get('address_id')
            delivery_date = request.form.get('delivery_date')
            start_time = request.form.get('start_time')
            end_time = request.form.get('end_time')
            notes = sanitize_input(request.form.get('notes', ''))

            if not all([driver_id, address_id, delivery_date, start_time, end_time]):
                flash(_("All fields are required"), "danger")
                return redirect(url_for('employee.edit_delivery', delivery_id=delivery_id))

            # Update delivery
            if DeliveryService.update_delivery(
                delivery_id=delivery_id,
                driver_id=int(driver_id),
                address_id=int(address_id),
                date=delivery_date,
                start_time=start_time,
                end_time=end_time,
                notes=notes
            ):
                flash(_("Delivery updated successfully"), "success")
            else:
                flash(_("Error updating delivery"), "danger")

            return redirect(url_for('employee.calendar'))

        # Get delivery details
        delivery = DeliveryService.get_delivery_by_id(delivery_id)
        if not delivery:
            flash(_("Delivery not found"), "danger")
            return redirect(url_for('employee.calendar'))

        drivers = get_all_drivers()
        addresses = get_all_addresses()

        return render_template('employee/edit_delivery.html',
                             delivery=delivery,
                             drivers=drivers,
                             addresses=addresses)
    except Exception as e:
        flash(_("Error processing delivery edit"), "danger")
        return redirect(url_for('employee.calendar'))

@employee_bp.route('/api/delivery-stats')
@login_required
@role_required('employee', 'manager')
def delivery_stats():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": _("Start and end dates are required")}), 400

        stats = DeliveryService.get_delivery_stats(start_date, end_date)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": _("Error fetching delivery statistics")}), 500

@employee_bp.route('/api/optimize-route/<int:driver_id>')
@login_required
@role_required('employee', 'manager')
def optimize_route(driver_id):
    try:
        delivery_date = request.args.get('date')
        if not delivery_date:
            return jsonify({"error": _("Date is required")}), 400

        optimized_route = DeliveryService.optimize_delivery_route(driver_id, delivery_date)
        return jsonify(optimized_route)
    except Exception as e:
        return jsonify({"error": _("Error optimizing route")}), 500

@employee_bp.route('/map-config', methods=['POST'])
@login_required
@role_required('employee', 'manager')
def configure_map():
    from app.extensions import db
    from app.models.map_config import MapConfig
    from flask import request, jsonify

    data = request.get_json()
    api_key = data.get('api_key')
    environment = data.get('environment')

    if not api_key or not environment:
        return jsonify({'error': 'API key and environment are required'}), 400

    # Validate API key by geocoding warehouse location
    import requests
    warehouse_lat = current_app.config['WAREHOUSE_LAT']
    warehouse_lng = current_app.config['WAREHOUSE_LNG']
    response = requests.get(
        f"https://maps.googleapis.com/maps/api/geocode/json?latlng={warehouse_lat},{warehouse_lng}&key={api_key}"
    )

    if response.status_code != 200 or response.json().get('status') != 'OK':
        return jsonify({'error': 'Invalid API key or quota exceeded'}), 400

    # Save to database
    map_config = MapConfig(api_key=api_key, environment=environment, last_validated=datetime.utcnow())
    db.session.add(map_config)
    db.session.commit()

    return jsonify({'message': 'API key configured successfully'}), 200

@employee_bp.route('/drivers', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'driver', 'employee'])
def get_drivers():
    """Fetch all drivers for the dropdown."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name FROM users WHERE role = 'driver' AND active = TRUE")
        drivers = cursor.fetchall()
        cursor.close()

        return jsonify({"drivers": [{"id": driver[0], "name": driver[1]} for driver in drivers]}), 200
    except Exception as e:
        logger.error(f"Error fetching drivers: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to fetch drivers."}), 500

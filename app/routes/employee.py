from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from datetime import datetime, date, timedelta
from typing import Dict, Any

from app.models.addresses import get_all_addresses, create_address, get_address_by_id
from app.models.users import get_all_drivers, get_user_by_id
from app.services.delivery_service import DeliveryService
from app.middleware import login_required, role_required, rate_limit_by_ip
from app.utils import validate_email, sanitize_input, format_datetime
from app import mysql

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
        flash("Error loading dashboard data", "danger")
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
                flash("Invalid coordinates", "danger")
                return redirect(url_for('employee.addresses'))

            if not all([label, street, city, zip_code]):
                flash("All fields are required", "danger")
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
                flash("Address added successfully", "success")
            else:
                flash("Error adding address", "danger")

        except Exception as e:
            flash("Error processing address", "danger")

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
                flash("All fields are required", "danger")
                return redirect(url_for('employee.schedule'))

            # Validate driver and address exist
            driver = get_user_by_id(driver_id)
            address = get_address_by_id(address_id)
            
            if not driver or not address:
                flash("Invalid driver or address", "danger")
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
                flash("Delivery scheduled successfully", "success")
            else:
                flash("Error scheduling delivery", "danger")

        except Exception as e:
            flash("Error processing delivery schedule", "danger")

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
                flash("Invalid date format", "warning")

        schedule = DeliveryService.get_all_deliveries_grouped(filter_driver, filter_date)
        return render_template('employee/calendar.html', schedule=schedule)
    except Exception as e:
        flash("Error loading calendar", "danger")
        return render_template('employee/calendar.html', schedule={})

@employee_bp.route('/delivery/<int:delivery_id>/delete', methods=['POST'])
@login_required
@role_required('employee', 'manager')
def delete_delivery_route(delivery_id):
    try:
        if DeliveryService.delete_delivery(delivery_id):
            flash("Delivery deleted successfully", "success")
        else:
            flash("Error deleting delivery", "danger")
    except Exception as e:
        flash("Error processing deletion", "danger")
    
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
                flash("All fields are required", "danger")
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
                flash("Delivery updated successfully", "success")
            else:
                flash("Error updating delivery", "danger")

            return redirect(url_for('employee.calendar'))

        # Get delivery details
        delivery = DeliveryService.get_delivery_by_id(delivery_id)
        if not delivery:
            flash("Delivery not found", "danger")
            return redirect(url_for('employee.calendar'))

        drivers = get_all_drivers()
        addresses = get_all_addresses()

        return render_template('employee/edit_delivery.html',
                             delivery=delivery,
                             drivers=drivers,
                             addresses=addresses)
    except Exception as e:
        flash("Error processing delivery edit", "danger")
        return redirect(url_for('employee.calendar'))

@employee_bp.route('/api/delivery-stats')
@login_required
@role_required('employee', 'manager')
def delivery_stats():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            return jsonify({"error": "Start and end dates are required"}), 400

        stats = DeliveryService.get_delivery_stats(start_date, end_date)
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": "Error fetching delivery statistics"}), 500

@employee_bp.route('/api/optimize-route/<int:driver_id>')
@login_required
@role_required('employee', 'manager')
def optimize_route(driver_id):
    try:
        delivery_date = request.args.get('date')
        if not delivery_date:
            return jsonify({"error": "Date is required"}), 400

        optimized_route = DeliveryService.optimize_delivery_route(driver_id, delivery_date)
        return jsonify(optimized_route)
    except Exception as e:
        return jsonify({"error": "Error optimizing route"}), 500

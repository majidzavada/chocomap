from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify, current_app
from flask_babel import _
from datetime import datetime, date, timedelta
from typing import Dict, Any
import logging

from app.models.addresses import get_all_addresses, create_address, get_address_by_id
from app.models.users import get_all_drivers, get_user_by_id
from app.services.delivery_service import DeliveryService
from app.middleware import login_required, role_required, rate_limit_by_ip
from app.utils import validate_email, sanitize_input, format_datetime, get_google_maps_api_key, get_warehouse_location
from app import mysql

logger = logging.getLogger(__name__)

employee_bp = Blueprint('employee', __name__, url_prefix='/employee')

@employee_bp.route('/dashboard')
@login_required
@role_required('employee', 'manager')
def dashboard():
    cursor = None
    try:
        # Get current date and time ranges
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        month_start = today.replace(day=1)
        
        cursor = mysql.connection.cursor()
        
        # Get today's delivery count
        cursor.execute("""
            SELECT COUNT(*) FROM deliveries 
            WHERE delivery_date = %s
        """, (today.isoformat(),))
        today_count = cursor.fetchone()[0]
        
        # Get this week's delivery count
        cursor.execute("""
            SELECT COUNT(*) FROM deliveries 
            WHERE delivery_date BETWEEN %s AND %s
        """, (week_start.isoformat(), week_end.isoformat()))
        week_count = cursor.fetchone()[0]
        
        # Get this month's delivery count
        cursor.execute("""
            SELECT COUNT(*) FROM deliveries 
            WHERE delivery_date >= %s
        """, (month_start.isoformat(),))
        month_count = cursor.fetchone()[0]
        
        # Get delivery status breakdown for today
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count
            FROM deliveries 
            WHERE delivery_date = %s
            GROUP BY status
        """, (today.isoformat(),))
        status_breakdown = {row['status']: row['count'] for row in cursor.fetchall()}
        
        # Get recent deliveries (last 5)
        cursor.execute("""
            SELECT 
                d.id,
                d.delivery_date,
                d.start_time,
                d.status,
                a.label as address_label,
                u.name as driver_name,
                d.created_at
            FROM deliveries d
            JOIN addresses a ON d.address_id = a.id
            JOIN users u ON d.driver_id = u.id
            ORDER BY d.created_at DESC
            LIMIT 5
        """)
        recent_deliveries = cursor.fetchall()
        
        # Get next upcoming delivery
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
        
        # Get active drivers count
        cursor.execute("""
            SELECT COUNT(*) FROM users 
            WHERE role = 'driver' AND active = TRUE
        """)
        active_drivers = cursor.fetchone()[0]
        
        # Get total addresses count
        cursor.execute("""
            SELECT COUNT(*) FROM addresses
        """)
        total_addresses = cursor.fetchone()[0]
        
        # Get weekly delivery trend (last 7 days)
        cursor.execute("""
            SELECT 
                delivery_date,
                COUNT(*) as count
            FROM deliveries 
            WHERE delivery_date >= %s
            GROUP BY delivery_date
            ORDER BY delivery_date
        """, ((today - timedelta(days=7)).isoformat(),))
        weekly_trend = cursor.fetchall()

        # Format datetime fields
        if next_delivery:
            next_delivery['delivery_date'] = format_datetime(next_delivery['delivery_date'])
            next_delivery['start_time'] = format_datetime(next_delivery['start_time'])
        
        for delivery in recent_deliveries:
            delivery['delivery_date'] = format_datetime(delivery['delivery_date'])
            delivery['start_time'] = format_datetime(delivery['start_time'])
            delivery['created_at'] = format_datetime(delivery['created_at'])

        # Prepare dashboard data
        dashboard_data = {
            'today_count': today_count,
            'week_count': week_count,
            'month_count': month_count,
            'status_breakdown': status_breakdown,
            'recent_deliveries': recent_deliveries,
            'next_delivery': next_delivery,
            'active_drivers': active_drivers,
            'total_addresses': total_addresses,
            'weekly_trend': weekly_trend
        }

        return render_template('employee/dashboard.html', **dashboard_data)
    except Exception as e:
        logger.error(f"Error loading dashboard data: {str(e)}", exc_info=True)
        flash(_("Error loading dashboard data"), "danger")
        return render_template('employee/dashboard.html', 
                             today_count=0, week_count=0, month_count=0,
                             status_breakdown={}, recent_deliveries=[],
                             next_delivery=None, active_drivers=0,
                             total_addresses=0, weekly_trend=[])
    finally:
        if cursor:
            cursor.close()

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

    from app.utils import get_google_maps_api_key
    addresses = get_all_addresses()
    return render_template('employee/addresses.html', addresses=addresses, get_google_maps_api_key=get_google_maps_api_key)

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
    google_maps_api_key = get_google_maps_api_key()
    warehouse_location = get_warehouse_location()
    today = date.today().isoformat()
    
    return render_template('employee/schedule.html',
                         drivers=drivers,
                         addresses=addresses,
                         google_maps_api_key=google_maps_api_key,
                         warehouse_location=warehouse_location,
                         today=today)

@employee_bp.route('/calendar')
@login_required
@role_required('employee', 'manager')
def calendar():
    try:
        filter_driver = request.args.get('driver')
        filter_date = request.args.get('date')
        filter_status = request.args.get('status')
        
        # Validate date format if provided
        if filter_date:
            try:
                datetime.strptime(filter_date, '%Y-%m-%d')
            except ValueError:
                filter_date = None
                flash(_("Invalid date format"), "warning")

        # Get deliveries with enhanced filtering
        cursor = None
        try:
            cursor = mysql.connection.cursor()
            
            query = """
                SELECT d.*, u.name AS driver_name, a.label, a.street_address, a.city
                FROM deliveries d
                JOIN users u ON d.driver_id = u.id
                JOIN addresses a ON d.address_id = a.id
                WHERE 1=1
            """
            params = []
            
            if filter_driver:
                query += " AND u.name LIKE %s"
                params.append(f"%{filter_driver}%")
            if filter_date:
                query += " AND d.delivery_date = %s"
                params.append(filter_date)
            if filter_status:
                query += " AND d.status = %s"
                params.append(filter_status)
                
            query += " ORDER BY d.delivery_date, d.start_time"
            
            cursor.execute(query, tuple(params))
            deliveries = cursor.fetchall()
            
            # Format datetime fields
            for delivery in deliveries:
                delivery['created_at'] = format_datetime(delivery['created_at'])
                delivery['updated_at'] = format_datetime(delivery['updated_at'])
                delivery['delivery_date'] = format_datetime(delivery['delivery_date'])
                if delivery['start_time']:
                    delivery['start_time'] = format_datetime(delivery['start_time'])
                if delivery['end_time']:
                    delivery['end_time'] = format_datetime(delivery['end_time'])
            
            # Group deliveries by date and driver
            schedule = {}
            for d in deliveries:
                key = (d['delivery_date'], d['driver_name'])
                if key not in schedule:
                    schedule[key] = []
                schedule[key].append(d)
            
            # Get all drivers for filter dropdown
            cursor.execute("SELECT DISTINCT id, name FROM users WHERE role = 'driver' AND active = TRUE ORDER BY name")
            drivers = cursor.fetchall()
        finally:
            if cursor:
                cursor.close()
        
        return render_template('employee/calendar.html', 
                             schedule=schedule, 
                             drivers=drivers)
    except Exception as e:
        logger.error(f"Error loading calendar: {str(e)}", exc_info=True)
        flash(_("Error loading calendar"), "danger")
        return render_template('employee/calendar.html', schedule={}, drivers=[])

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

        cursor = mysql.connection.cursor()
        
        # Get comprehensive delivery statistics
        cursor.execute("""
            SELECT 
                COUNT(*) as total_deliveries,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_deliveries,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_deliveries,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending_deliveries,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_deliveries,
                AVG(CASE 
                    WHEN status = 'completed' 
                    THEN TIMESTAMPDIFF(MINUTE, created_at, updated_at)
                END) as avg_processing_time,
                AVG(eta_minutes) as avg_eta,
                MIN(delivery_date) as earliest_delivery,
                MAX(delivery_date) as latest_delivery
            FROM deliveries
            WHERE delivery_date BETWEEN %s AND %s
        """, (start_date, end_date))
        
        stats = cursor.fetchone()
        
        # Get daily breakdown
        cursor.execute("""
            SELECT 
                delivery_date,
                COUNT(*) as total,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled
            FROM deliveries
            WHERE delivery_date BETWEEN %s AND %s
            GROUP BY delivery_date
            ORDER BY delivery_date
        """, (start_date, end_date))
        
        daily_breakdown = cursor.fetchall()
        
        # Get driver performance
        cursor.execute("""
            SELECT 
                u.name as driver_name,
                COUNT(*) as total_deliveries,
                COUNT(CASE WHEN d.status = 'completed' THEN 1 END) as completed_deliveries,
                AVG(d.eta_minutes) as avg_eta
            FROM deliveries d
            JOIN users u ON d.driver_id = u.id
            WHERE d.delivery_date BETWEEN %s AND %s
            GROUP BY u.id, u.name
            ORDER BY completed_deliveries DESC
        """, (start_date, end_date))
        
        driver_performance = cursor.fetchall()
        
        cursor.close()
        
        result = {
            'total_deliveries': stats['total_deliveries'] or 0,
            'completed_deliveries': stats['completed_deliveries'] or 0,
            'cancelled_deliveries': stats['cancelled_deliveries'] or 0,
            'pending_deliveries': stats['pending_deliveries'] or 0,
            'in_progress_deliveries': stats['in_progress_deliveries'] or 0,
            'avg_processing_time': float(stats['avg_processing_time'] or 0),
            'avg_eta': float(stats['avg_eta'] or 0),
            'earliest_delivery': stats['earliest_delivery'].isoformat() if stats['earliest_delivery'] else None,
            'latest_delivery': stats['latest_delivery'].isoformat() if stats['latest_delivery'] else None,
            'daily_breakdown': daily_breakdown,
            'driver_performance': driver_performance,
            'completion_rate': (stats['completed_deliveries'] / stats['total_deliveries'] * 100) if stats['total_deliveries'] > 0 else 0
        }
        
        return jsonify(result)
    except Exception as e:
        logger.error(f"Error fetching delivery statistics: {str(e)}", exc_info=True)
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
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        environment = data.get('environment')

        if not api_key or not environment:
            return jsonify({'error': 'API key and environment are required'}), 400

        # Validate API key by geocoding warehouse location
        import requests
        warehouse_lat = current_app.config.get('WAREHOUSE_LAT', '50.0755')
        warehouse_lng = current_app.config.get('WAREHOUSE_LNG', '14.4378')
        
        try:
            response = requests.get(
                f"https://maps.googleapis.com/maps/api/geocode/json?latlng={warehouse_lat},{warehouse_lng}&key={api_key}",
                timeout=10
            )
            
            if response.status_code != 200 or response.json().get('status') != 'OK':
                return jsonify({'error': 'Invalid API key or quota exceeded'}), 400
        except requests.RequestException:
            return jsonify({'error': 'Unable to validate API key'}), 400

        # Save to database using MySQL cursor
        cursor = mysql.connection.cursor()
        try:
            # Check if map_config table exists, if not create it
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS map_config (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    api_key VARCHAR(255) NOT NULL,
                    environment VARCHAR(50) NOT NULL,
                    last_validated DATETIME NOT NULL,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
                )
            """)
            
            # Insert or update the configuration
            cursor.execute("""
                INSERT INTO map_config (api_key, environment, last_validated)
                VALUES (%s, %s, NOW())
                ON DUPLICATE KEY UPDATE
                api_key = VALUES(api_key),
                environment = VALUES(environment),
                last_validated = VALUES(last_validated),
                updated_at = NOW()
            """, (api_key, environment))
            
            mysql.connection.commit()
            cursor.close()
            
            return jsonify({'message': 'API key configured successfully'}), 200
            
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error saving map config: {str(e)}")
            return jsonify({'error': 'Error saving configuration'}), 500
        finally:
            cursor.close()
            
    except Exception as e:
        logger.error(f"Error configuring map: {str(e)}")
        return jsonify({'error': 'Error processing map configuration'}), 500

@employee_bp.route('/drivers', methods=['GET'])
@login_required
@role_required(['admin', 'manager', 'driver', 'employee'])
def get_drivers():
    """Fetch all drivers for the dropdown."""
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name FROM users WHERE role = 'driver' AND active = TRUE")
        drivers = cursor.fetchall()

        return jsonify({"drivers": [{"id": driver[0], "name": driver[1]} for driver in drivers]}), 200
    except Exception as e:
        logger.error(f"Error fetching drivers: {str(e)}", exc_info=True)
        return jsonify({"error": "Failed to fetch drivers."}), 500
    finally:
        if cursor:
            cursor.close()

@employee_bp.route('/api/dashboard-updates')
@login_required
@role_required('employee', 'manager')
def dashboard_updates():
    """Get real-time dashboard updates"""
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        today = date.today()
        
        # Get quick stats
        cursor.execute("""
            SELECT 
                COUNT(*) as today_total,
                COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed
            FROM deliveries 
            WHERE delivery_date = %s
        """, (today.isoformat(),))
        
        stats = cursor.fetchone()
        
        # Get latest delivery update
        cursor.execute("""
            SELECT 
                d.id,
                d.status,
                d.updated_at,
                a.label as address_label,
                u.name as driver_name
            FROM deliveries d
            JOIN addresses a ON d.address_id = a.id
            JOIN users u ON d.driver_id = u.id
            ORDER BY d.updated_at DESC
            LIMIT 1
        """)
        
        latest_update = cursor.fetchone()
        if latest_update:
            latest_update['updated_at'] = format_datetime(latest_update['updated_at'])
        
        return jsonify({
            'today_stats': stats,
            'latest_update': latest_update,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"Error fetching dashboard updates: {str(e)}", exc_info=True)
        return jsonify({"error": _("Error fetching updates")}), 500
    finally:
        if cursor:
            cursor.close()

@employee_bp.route('/api/search')
@login_required
@role_required('employee', 'manager')
def search():
    """Search deliveries, addresses, and drivers"""
    try:
        query = request.args.get('q', '').strip()
        search_type = request.args.get('type', 'all')
        limit = min(int(request.args.get('limit', 10)), 50)
        
        if not query or len(query) < 2:
            return jsonify({"error": _("Search query must be at least 2 characters")}), 400
        
        cursor = mysql.connection.cursor()
        results = {}
        
        if search_type in ['all', 'deliveries']:
            # Search deliveries
            cursor.execute("""
                SELECT 
                    d.id,
                    d.delivery_date,
                    d.status,
                    a.label as address_label,
                    u.name as driver_name
                FROM deliveries d
                JOIN addresses a ON d.address_id = a.id
                JOIN users u ON d.driver_id = u.id
                WHERE a.label LIKE %s OR u.name LIKE %s OR d.notes LIKE %s
                ORDER BY d.delivery_date DESC
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            
            results['deliveries'] = cursor.fetchall()
        
        if search_type in ['all', 'addresses']:
            # Search addresses
            cursor.execute("""
                SELECT id, label, street_address, city, zip_code
                FROM addresses
                WHERE label LIKE %s OR street_address LIKE %s OR city LIKE %s
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
            
            results['addresses'] = cursor.fetchall()
        
        if search_type in ['all', 'drivers']:
            # Search drivers
            cursor.execute("""
                SELECT id, name, email
                FROM users
                WHERE role = 'driver' AND active = TRUE
                AND (name LIKE %s OR email LIKE %s)
                LIMIT %s
            """, (f"%{query}%", f"%{query}%", limit))
            
            results['drivers'] = cursor.fetchall()
        
        cursor.close()
        return jsonify(results)
    except Exception as e:
        logger.error(f"Error performing search: {str(e)}", exc_info=True)
        return jsonify({"error": _("Error performing search")}), 500

@employee_bp.route('/api/bulk-operations', methods=['POST'])
@login_required
@role_required('employee', 'manager')
def bulk_operations():
    """Handle bulk operations on deliveries"""
    try:
        data = request.get_json()
        operation = data.get('operation')
        delivery_ids = data.get('delivery_ids', [])
        
        if not operation or not delivery_ids:
            return jsonify({"error": _("Operation and delivery IDs are required")}), 400
        
        cursor = mysql.connection.cursor()
        success_count = 0
        
        if operation == 'cancel':
            for delivery_id in delivery_ids:
                cursor.execute("""
                    UPDATE deliveries 
                    SET status = 'cancelled', updated_at = NOW()
                    WHERE id = %s AND status = 'pending'
                """, (delivery_id,))
                if cursor.rowcount > 0:
                    success_count += 1
        
        elif operation == 'reschedule':
            new_date = data.get('new_date')
            if not new_date:
                return jsonify({"error": _("New date is required for rescheduling")}), 400
            
            for delivery_id in delivery_ids:
                cursor.execute("""
                    UPDATE deliveries 
                    SET delivery_date = %s, updated_at = NOW()
                    WHERE id = %s AND status = 'pending'
                """, (new_date, delivery_id))
                if cursor.rowcount > 0:
                    success_count += 1
        
        elif operation == 'assign_driver':
            new_driver_id = data.get('driver_id')
            if not new_driver_id:
                return jsonify({"error": _("Driver ID is required")}), 400
            
            for delivery_id in delivery_ids:
                cursor.execute("""
                    UPDATE deliveries 
                    SET driver_id = %s, updated_at = NOW()
                    WHERE id = %s AND status = 'pending'
                """, (new_driver_id, delivery_id))
                if cursor.rowcount > 0:
                    success_count += 1
        
        else:
            return jsonify({"error": _("Invalid operation")}), 400
        
        mysql.connection.commit()
        cursor.close()
        
        return jsonify({
            "success": True,
            "message": _("Successfully updated {} deliveries").format(success_count),
            "updated_count": success_count
        })
    except Exception as e:
        mysql.connection.rollback()
        logger.error(f"Error performing bulk operation: {str(e)}", exc_info=True)
        return jsonify({"error": _("Error performing bulk operation")}), 500

@employee_bp.route('/api/delivery-trends')
@login_required
@role_required('employee', 'manager')
def delivery_trends():
    """Get delivery trends for analytics"""
    try:
        days = int(request.args.get('days', 30))
        cursor = mysql.connection.cursor()
        
        # Get daily delivery counts for the past X days
        cursor.execute("""
            SELECT 
                delivery_date,
                COUNT(*) as total_deliveries,
                COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_deliveries,
                AVG(eta_minutes) as avg_eta
            FROM deliveries
            WHERE delivery_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY delivery_date
            ORDER BY delivery_date
        """, (days,))
        
        daily_trends = cursor.fetchall()
        
        # Get hourly patterns
        cursor.execute("""
            SELECT 
                HOUR(start_time) as hour,
                COUNT(*) as delivery_count
            FROM deliveries
            WHERE delivery_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY HOUR(start_time)
            ORDER BY hour
        """, (days,))
        
        hourly_patterns = cursor.fetchall()
        
        # Get status distribution
        cursor.execute("""
            SELECT 
                status,
                COUNT(*) as count
            FROM deliveries
            WHERE delivery_date >= DATE_SUB(CURDATE(), INTERVAL %s DAY)
            GROUP BY status
        """, (days,))
        
        status_distribution = cursor.fetchall()
        
        cursor.close()
        
        return jsonify({
            'daily_trends': daily_trends,
            'hourly_patterns': hourly_patterns,
            'status_distribution': status_distribution
        })
    except Exception as e:
        logger.error(f"Error fetching delivery trends: {str(e)}", exc_info=True)
        return jsonify({"error": _("Error fetching trends")}), 500

@employee_bp.route('/api/export-data')
@login_required
@role_required('employee', 'manager')
def export_data():
    """Export delivery data as CSV"""
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        format_type = request.args.get('format', 'csv')
        
        if not start_date or not end_date:
            return jsonify({"error": _("Start and end dates are required")}), 400
        
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                d.id,
                d.delivery_date,
                d.start_time,
                d.end_time,
                d.status,
                a.label as address_label,
                a.street_address,
                a.city,
                a.zip_code,
                u.name as driver_name,
                d.notes,
                d.eta_minutes,
                d.created_at,
                d.updated_at
            FROM deliveries d
            JOIN addresses a ON d.address_id = a.id
            JOIN users u ON d.driver_id = u.id
            WHERE d.delivery_date BETWEEN %s AND %s
            ORDER BY d.delivery_date, d.start_time
        """, (start_date, end_date))
        
        deliveries = cursor.fetchall()
        cursor.close()
        
        if format_type == 'csv':
            import csv
            import io
            
            output = io.StringIO()
            writer = csv.writer(output)
            
            # Write header
            writer.writerow([
                'ID', 'Date', 'Start Time', 'End Time', 'Status',
                'Address Label', 'Street Address', 'City', 'ZIP Code',
                'Driver Name', 'Notes', 'ETA (minutes)', 'Created', 'Updated'
            ])
            
            # Write data
            for delivery in deliveries:
                writer.writerow([
                    delivery['id'],
                    delivery['delivery_date'],
                    delivery['start_time'],
                    delivery['end_time'],
                    delivery['status'],
                    delivery['address_label'],
                    delivery['street_address'],
                    delivery['city'],
                    delivery['zip_code'],
                    delivery['driver_name'],
                    delivery['notes'],
                    delivery['eta_minutes'],
                    delivery['created_at'],
                    delivery['updated_at']
                ])
            
            output_str = output.getvalue()
            output.close()
            
            from flask import Response
            return Response(
                output_str,
                mimetype='text/csv',
                headers={'Content-Disposition': f'attachment; filename=deliveries_{start_date}_to_{end_date}.csv'}
            )
        
        else:
            return jsonify({'deliveries': deliveries})
    
    except Exception as e:
        logger.error(f"Error exporting data: {str(e)}", exc_info=True)
        return jsonify({"error": _("Error exporting data")}), 500

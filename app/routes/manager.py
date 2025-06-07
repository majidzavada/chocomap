from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from flask_babel import _
from datetime import datetime, date, timedelta
from app.services.delivery_service import DeliveryService
from app.services.user_service import UserService
from app.services.address_service import AddressService
from app.services.analytics_service import AnalyticsService
from app.middleware import login_required, role_required, rate_limit_by_ip
from app.utils import format_datetime
import logging

logger = logging.getLogger(__name__)
manager_bp = Blueprint('manager', __name__, url_prefix='/manager')

@manager_bp.route('/dashboard')
@login_required
@role_required('manager')
def dashboard():
    try:
        # Get delivery analytics
        end_date = date.today()
        start_date = end_date - timedelta(days=30)
        delivery_analytics = AnalyticsService.get_delivery_analytics(
            start_date.isoformat(),
            end_date.isoformat()
        )
        
        # Get user analytics
        user_analytics = AnalyticsService.get_user_analytics()
        
        # Get system health
        system_health = AnalyticsService.get_system_health()
        
        return render_template('manager/dashboard.html',
                             delivery_analytics=delivery_analytics,
                             user_analytics=user_analytics,
                             system_health=system_health)
    except Exception as e:
        logger.error(f"Error loading manager dashboard: {str(e)}")
        flash(_("Error loading dashboard"), "danger")
        return render_template('manager/dashboard.html')

@manager_bp.route('/drivers')
@login_required
@role_required('manager')
def drivers():
    try:
        drivers = UserService.get_users_by_role('driver')
        return render_template('manager/drivers.html', drivers=drivers)
    except Exception as e:
        logger.error(f"Error loading drivers: {str(e)}")
        flash(_("Error loading drivers"), "danger")
        return render_template('manager/drivers.html')

@manager_bp.route('/driver/<int:driver_id>/stats')
@login_required
@role_required('manager')
def driver_stats(driver_id):
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            start_date = start_date.isoformat()
            end_date = end_date.isoformat()
            
        stats = DeliveryService.get_driver_stats(
            driver_id=driver_id,
            start_date=start_date,
            end_date=end_date
        )
        
        driver = UserService.get_user_by_id(driver_id)
        return render_template('manager/driver_stats.html',
                             stats=stats,
                             driver=driver,
                             start_date=start_date,
                             end_date=end_date)
    except Exception as e:
        logger.error(f"Error loading driver stats: {str(e)}")
        flash(_("Error loading driver statistics"), "danger")
        return redirect(url_for('manager.drivers'))

@manager_bp.route('/addresses', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def addresses():
    if request.method == 'POST':
        try:
            from app.utils import sanitize_input
            from app.models.addresses import create_address
            
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
                return redirect(url_for('manager.addresses'))

            if not all([label, street, city, zip_code]):
                flash(_("All fields are required"), "danger")
                return redirect(url_for('manager.addresses'))

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
            logger.error(f"Error creating address: {str(e)}")
            flash(_("Error processing address"), "danger")
        return redirect(url_for('manager.addresses'))
    
    try:
        from app.utils import get_google_maps_api_key
        addresses = AddressService.get_all_addresses()
        return render_template('manager/addresses.html', addresses=addresses, get_google_maps_api_key=get_google_maps_api_key)
    except Exception as e:
        logger.error(f"Error loading addresses: {str(e)}")
        flash(_("Error loading addresses"), "danger")
        return render_template('manager/addresses.html', get_google_maps_api_key=get_google_maps_api_key)

@manager_bp.route('/address/<int:address_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('manager')
def edit_address(address_id):
    try:
        if request.method == 'POST':
            street = request.form.get('street')
            city = request.form.get('city')
            zip_code = request.form.get('zip_code')
            
            if AddressService.update_address(
                address_id=address_id,
                street=street,
                city=city,
                zip_code=zip_code
            ):
                flash(_("Address updated successfully"), "success")
            else:
                flash(_("Error updating address"), "danger")
                
            return redirect(url_for('manager.addresses'))
            
        address = AddressService.get_address_by_id(address_id)
        return render_template('manager/edit_address.html', address=address)
    except Exception as e:
        logger.error(f"Error editing address: {str(e)}")
        flash(_("Error loading address"), "danger")
        return redirect(url_for('manager.addresses'))

@manager_bp.route('/reports')
@login_required
@role_required('manager')
def reports():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            end_date = date.today()
            start_date = end_date - timedelta(days=30)
            start_date = start_date.isoformat()
            end_date = end_date.isoformat()
            
        # Get delivery analytics
        delivery_analytics = AnalyticsService.get_delivery_analytics(
            start_date,
            end_date
        )
        
        # Get user analytics
        user_analytics = AnalyticsService.get_user_analytics()
        
        return render_template('manager/reports.html',
                             delivery_analytics=delivery_analytics,
                             user_analytics=user_analytics,
                             start_date=start_date,
                             end_date=end_date)
    except Exception as e:
        logger.error(f"Error loading reports: {str(e)}")
        flash(_("Error loading reports"), "danger")
        return render_template('manager/reports.html')

@manager_bp.route('/api/system-health')
@login_required
@role_required('manager')
def get_system_health():
    try:
        health_data = AnalyticsService.get_system_health()
        return jsonify(health_data)
    except Exception as e:
        logger.error(f"Error getting system health: {str(e)}")
        return jsonify({"error": _("Internal server error")}), 500

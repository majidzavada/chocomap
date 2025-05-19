from flask import Blueprint, render_template, session, redirect, url_for, request, flash, jsonify
from datetime import datetime, date, timedelta
from app.services.delivery_service import DeliveryService
from app.services.user_service import UserService
from app.middleware import login_required, role_required, rate_limit_by_ip
from app.utils import format_datetime
import logging

logger = logging.getLogger(__name__)
driver_bp = Blueprint('driver', __name__, url_prefix='/driver')

@driver_bp.route('/dashboard')
@login_required
@role_required('driver')
def dashboard():
    try:
        # Get today's deliveries
        today = date.today().isoformat()
        deliveries = DeliveryService.get_driver_deliveries(
            driver_id=session['user_id'],
            date=today
        )
        
        # Get driver stats
        stats = DeliveryService.get_driver_stats(session['user_id'])
        
        return render_template('driver/dashboard.html',
                             deliveries=deliveries,
                             stats=stats)
    except Exception as e:
        logger.error(f"Error loading driver dashboard: {str(e)}")
        flash("Error loading dashboard", "danger")
        return render_template('driver/dashboard.html')

@driver_bp.route('/deliveries')
@login_required
@role_required('driver')
def deliveries():
    try:
        date_filter = request.args.get('date')
        status_filter = request.args.get('status')
        
        deliveries = DeliveryService.get_driver_deliveries(
            driver_id=session['user_id'],
            date=date_filter,
            status=status_filter
        )
        
        return render_template('driver/deliveries.html',
                             deliveries=deliveries)
    except Exception as e:
        logger.error(f"Error loading deliveries: {str(e)}")
        flash("Error loading deliveries", "danger")
        return render_template('driver/deliveries.html')

@driver_bp.route('/delivery/<int:delivery_id>/update-status', methods=['POST'])
@login_required
@role_required('driver')
@rate_limit_by_ip("30 per minute")
def update_delivery_status(delivery_id):
    try:
        status = request.form.get('status')
        if not status:
            return jsonify({"error": "Status is required"}), 400
            
        if DeliveryService.update_delivery_status(delivery_id, status):
            # Track activity
            UserService.track_user_activity(
                session['user_id'],
                'update_delivery_status',
                {'delivery_id': delivery_id, 'status': status}
            )
            return jsonify({"message": "Status updated successfully"})
        else:
            return jsonify({"error": "Error updating status"}), 400
    except Exception as e:
        logger.error(f"Error updating delivery status: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

@driver_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('driver')
def profile():
    try:
        if request.method == 'POST':
            name = request.form.get('name')
            email = request.form.get('email')
            phone = request.form.get('phone')
            
            if UserService.update_user(
                user_id=session['user_id'],
                name=name,
                email=email,
                phone=phone
            ):
                flash("Profile updated successfully", "success")
            else:
                flash("Error updating profile", "danger")
                
            return redirect(url_for('driver.profile'))
            
        # Get user profile
        user = UserService.get_user_by_id(session['user_id'])
        return render_template('driver/profile.html', user=user)
    except Exception as e:
        logger.error(f"Error in profile management: {str(e)}")
        flash("Error loading profile", "danger")
        return redirect(url_for('driver.dashboard'))

@driver_bp.route('/stats')
@login_required
@role_required('driver')
def stats():
    try:
        start_date = request.args.get('start_date')
        end_date = request.args.get('end_date')
        
        if not start_date or not end_date:
            start_date = (date.today() - timedelta(days=30)).isoformat()
            end_date = date.today().isoformat()
            
        stats = DeliveryService.get_driver_stats(
            driver_id=session['user_id'],
            start_date=start_date,
            end_date=end_date
        )
        
        return render_template('driver/stats.html',
                             stats=stats,
                             start_date=start_date,
                             end_date=end_date)
    except Exception as e:
        logger.error(f"Error loading driver stats: {str(e)}")
        flash("Error loading statistics", "danger")
        return render_template('driver/stats.html')

@driver_bp.route('/api/delivery-route/<int:delivery_id>')
@login_required
@role_required('driver')
def get_delivery_route(delivery_id):
    try:
        route = DeliveryService.get_delivery_route(delivery_id)
        if route:
            return jsonify(route)
        else:
            return jsonify({"error": "Route not found"}), 404
    except Exception as e:
        logger.error(f"Error getting delivery route: {str(e)}")
        return jsonify({"error": "Internal server error"}), 500

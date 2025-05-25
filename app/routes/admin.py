from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify, current_app
from flask_babel import _
from app.models.users import User
from app.middleware import login_required, role_required, rate_limit_by_ip
from app.utils import validate_email, sanitize_input
from app.services.user_service import UserService
from datetime import datetime, date, timedelta
from app import mysql
import logging
import os
import json

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@login_required
@role_required('admin')
def index():
    return render_template('admin/index.html')

@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    """Admin dashboard with full system control"""
    try:
        # Get system statistics
        user_stats = UserService.get_user_stats()
        
        # Get pending registrations
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, email, username, role, created_at
            FROM users
            WHERE approval_status = 'pending'
            ORDER BY created_at DESC
        """)
        pending_registrations = []
        results = cursor.fetchall()
        for row in results:
            pending_registrations.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'username': row[3],
                'role': row[4],
                'created_at': row[5]
            })
        cursor.close()
        
        return render_template('admin/dashboard.html',
                             user_stats=user_stats,
                             pending_registrations=pending_registrations)
    except Exception as e:
        logger.error(f"Error loading admin dashboard: {str(e)}", exc_info=True)
        flash(_("Error loading dashboard"), "danger")
        return render_template('admin/dashboard.html')

@admin_bp.route('/users')
@login_required
@role_required('admin')
def users():
    """Admin user management"""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, email, username, role, active, approval_status, created_at
            FROM users
            ORDER BY id ASC
        """)
        users = []
        results = cursor.fetchall()
        for row in results:
            users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'username': row[3],
                'role': row[4],
                'active': row[5],
                'approval_status': row[6],
                'created_at': row[7]
            })
        cursor.close()
        
        return render_template('admin/users.html', users=users)
    except Exception as e:
        logger.error(f"Error loading admin users: {str(e)}", exc_info=True)
        flash(_("Error loading users"), "danger")
        return render_template('admin/users.html', users=[])

@admin_bp.route('/users/pending')
@login_required
@role_required('admin')
def pending_users():
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, email, username, role, created_at
            FROM users
            WHERE approval_status = 'pending'
            ORDER BY created_at DESC
        """)
        users = []
        results = cursor.fetchall()
        for row in results:
            users.append({
                'id': row[0],
                'name': row[1],
                'email': row[2],
                'username': row[3],
                'role': row[4],
                'created_at': row[5]
            })
        cursor.close()
        return render_template('admin/pending_users.html', users=users)
    except Exception as e:
        logger.error(f"Error loading pending users: {str(e)}", exc_info=True)
        flash(_("Error loading pending users"), "danger")
        return render_template('admin/pending_users.html', users=[])

@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def approve_user(user_id):
    """Approve a user registration"""
    try:
        UserService.update_user(user_id, status='active', approval_status='approved')
        flash(_("User approved successfully"), "success")
    except Exception as e:
        logger.error(f"Error approving user: {str(e)}", exc_info=True)
        flash(_("Error approving user"), "danger")
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_user(user_id):
    try:
        UserService.update_user(user_id, status='inactive', approval_status='rejected')
        flash(_("User rejected successfully"), "success")
    except Exception as e:
        logger.error(f"Error rejecting user: {str(e)}", exc_info=True)
        flash(_("Error rejecting user"), "danger")
    
    return redirect(url_for('admin.pending_users'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_user(user_id):
    try:
        cursor = mysql.connection.cursor()
        
        # Get user details
        cursor.execute("""
            SELECT id, name, email, username, role, active, approval_status
            FROM users
            WHERE id = %s
        """, (user_id,))
        result = cursor.fetchone()
        if not result:
            flash(_("User not found"), "danger")
            return redirect(url_for('admin.users'))
            
        user = {
            'id': result[0],
            'name': result[1],
            'email': result[2],
            'username': result[3],
            'role': result[4],
            'active': result[5],
            'approval_status': result[6]
        }
        
        if request.method == 'POST':
            name = sanitize_input(request.form.get('name', ''))
            email = request.form.get('email', '').strip()
            username = sanitize_input(request.form.get('username', '')).strip()
            role = request.form.get('role', '')
            active = 'active' in request.form  # Checkbox
            approval_status = request.form.get('approval_status', '')
            
            if not all([name, email, username, role, approval_status]):
                flash(_("All fields are required"), "danger")
                return redirect(url_for('admin.edit_user', user_id=user_id))
            if not validate_email(email):
                flash(_("Invalid email format"), "danger")
                return redirect(url_for('admin.edit_user', user_id=user_id))
            # Check for duplicate username (if changed)
            cursor.execute("SELECT id FROM users WHERE username = %s AND id != %s", (username, user_id))
            if cursor.fetchone():
                flash(_("A user with this username already exists."), "danger")
                return redirect(url_for('admin.edit_user', user_id=user_id))
            if UserService.update_user(user_id, name=name, email=email, username=username, role=role, active=active, approval_status=approval_status):
                flash(_("User updated successfully"), "success")
                return redirect(url_for('admin.users'))
            else:
                flash(_("Error updating user"), "danger")
                return redirect(url_for('admin.edit_user', user_id=user_id))
                
        cursor.close()
        return render_template('admin/edit_user.html', user=user)
        
    except Exception as e:
        logger.error(f"Error editing user: {str(e)}", exc_info=True)
        flash(_("Error editing user"), "danger")
        return redirect(url_for('admin.users'))

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_user(user_id):
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM users WHERE id = %s", (user_id,))
        mysql.connection.commit()
        affected_rows = cursor.rowcount
        cursor.close()
        
        if affected_rows > 0:
            flash(_("User deleted successfully"), "success")
        else:
            flash(_("User not found"), "danger")
            
    except Exception as e:
        mysql.connection.rollback()
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        flash(_("Error deleting user"), "danger")
        
    return redirect(url_for('admin.users'))

@admin_bp.route('/impersonate/<int:user_id>')
@login_required
@role_required('admin')
def impersonate_user(user_id):
    """Impersonate another user"""
    try:
        # Store admin's original ID for returning later
        if 'original_user_id' not in session:
            session['original_user_id'] = session['user_id']
            session['original_user_role'] = session['user_role']
        
        # Get user details
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT id, name, email, role 
            FROM users 
            WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()
        cursor.close()
        
        if not user:
            flash(_("User not found"), "danger")
            return redirect(url_for('admin.users'))
        
        # Set session to impersonated user
        session['user_id'] = user[0]
        session['name'] = user[1]
        session['user_role'] = user[3]
        session['is_impersonating'] = True
        
        flash(_("You are now impersonating {name}").format(name=user[1]), "warning")
        
        # Redirect to appropriate dashboard
        if user[3] == 'manager':
            return redirect(url_for('manager.dashboard'))
        elif user[3] == 'driver':
            return redirect(url_for('driver.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
            
    except Exception as e:
        logger.error(f"Error impersonating user: {str(e)}", exc_info=True)
        flash(_("Error impersonating user"), "danger")
        return redirect(url_for('admin.users'))

@admin_bp.route('/stop-impersonating')
@login_required
def stop_impersonating():
    """Stop impersonating and return to admin account"""
    if 'original_user_id' in session and 'is_impersonating' in session:
        # Restore original admin user
        session['user_id'] = session.pop('original_user_id')
        session['user_role'] = session.pop('original_user_role')
        session.pop('is_impersonating', None)
        
        flash(_("Returned to admin account"), "info")
    
    return redirect(url_for('admin.dashboard'))

# -------------------- Create New User --------------------

@admin_bp.route('/users/create', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def create_user_route():
    """Allow admin to create a new user and assign role"""
    if request.method == 'POST':
        try:
            name = sanitize_input(request.form.get('name', ''))
            email = request.form.get('email', '').strip()
            username = sanitize_input(request.form.get('username', '')).strip()
            role = request.form.get('role', 'employee')
            password = request.form.get('password', '').strip()

            if not all([name, email, username, password, role]):
                flash(_("All fields are required"), "danger")
                return redirect(url_for('admin.create_user_route'))

            # Check for duplicate email or username
            from app.models.users import get_user_by_email, get_user_by_id
            if get_user_by_email(email):
                flash(_("A user with this email already exists."), "danger")
                return redirect(url_for('admin.create_user_route'))
            cursor = mysql.connection.cursor()
            cursor.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cursor.fetchone():
                cursor.close()
                flash(_("A user with this username already exists."), "danger")
                return redirect(url_for('admin.create_user_route'))
            cursor.close()

            # Validate password strength
            from app.utils import is_valid_password
            is_valid, message = is_valid_password(password)
            if not is_valid:
                flash(_(message), "danger")
                return redirect(url_for('admin.create_user_route'))

            # Validate role
            allowed_roles = ['driver', 'manager', 'admin', 'employee']
            if role not in allowed_roles:
                flash(_("Invalid role selected. Allowed roles are: %(roles)s", roles=', '.join(allowed_roles)), "danger")
                return redirect(url_for('admin.create_user_route'))

            # Improved error handling
            try:
                # Log the role value
                logger.debug(f"Creating user with role: {role}")
                new_id = UserService.create_user(name=name, email=email, username=username, password=password, role=role)
                if new_id:
                    UserService.update_user(new_id, approval_status='approved', active=True)
                    flash(_("User created successfully"), "success")
                    return redirect(url_for('admin.users'))
                else:
                    flash(_("Error creating user. Please check the form and try again."), "danger")
            except Exception as e:
                logger.error(f'Error creating user: {str(e)}', exc_info=True)
                flash(_("Error creating user: %(error)s", error=str(e)), "danger")
        except Exception as e:
            logger.error(f'Error creating user: {str(e)}', exc_info=True)
            flash(_("Error creating user: %(error)s", error=str(e)), "danger")

    return render_template('admin/create_user.html')

@admin_bp.route('/logs', methods=['GET'])
@login_required
@role_required('admin')
def view_logs():
    """Serve logs for the admin dashboard."""
    try:
        log_file_path = '/home/choco/chocomap/logs/chocomap.log'  # Example log file
        with open(log_file_path, 'r') as log_file:
            logs = log_file.readlines()
        return jsonify({'logs': logs[-100:]})  # Return the last 100 log lines
    except Exception as e:
        current_app.logger.error(f"Error reading logs: {str(e)}")
        return jsonify({'error': 'Unable to fetch logs'}), 500

@admin_bp.route('/database/maintenance', methods=['GET', 'POST'])
def database_maintenance():
    """Handle database maintenance actions."""
    if request.method == 'POST':
        action = request.json.get('action')
        try:
            if action == 'backup':
                # Example: Backup database
                backup_file = f"/home/choco/chocomap/backups/db_backup_{datetime.now().strftime('%Y%m%d%H%M%S')}.sql"
                os.system(f"mysqldump -u root -pYOUR_PASSWORD chocomap > {backup_file}")
                return jsonify({'message': 'Database backup created successfully.', 'file': backup_file})
            elif action == 'restore':
                # Example: Restore database (requires file path in request)
                restore_file = request.json.get('file')
                os.system(f"mysql -u root -pYOUR_PASSWORD chocomap < {restore_file}")
                return jsonify({'message': 'Database restored successfully.'})
            else:
                return jsonify({'error': 'Invalid action.'}), 400
        except Exception as e:
            current_app.logger.error(f"Error during database maintenance: {str(e)}")
            return jsonify({'error': 'Database maintenance failed.'}), 500
    return jsonify({'message': 'Database maintenance endpoint.'})

@admin_bp.route('/system/settings', methods=['GET', 'POST'])
def system_settings():
    """Manage system settings."""
    if request.method == 'POST':
        settings_type = request.json.get('type')
        settings_data = request.json.get('data')
        try:
            if settings_type == 'application':
                # Save application settings (e.g., logging, debugging)
                with open('/home/choco/chocomap/config/app_settings.json', 'w') as f:
                    json.dump(settings_data, f)
                return jsonify({'message': 'Application settings updated successfully.'})
            elif settings_type == 'email':
                # Save email server settings
                with open('/home/choco/chocomap/config/email_settings.json', 'w') as f:
                    json.dump(settings_data, f)
                return jsonify({'message': 'Email server settings updated successfully.'})
            elif settings_type == 'api_keys':
                # Save API keys
                with open('/home/choco/chocomap/config/api_keys.json', 'w') as f:
                    json.dump(settings_data, f)
                return jsonify({'message': 'API keys updated successfully.'})
            else:
                return jsonify({'error': 'Invalid settings type.'}), 400
        except Exception as e:
            current_app.logger.error(f"Error updating settings: {str(e)}")
            return jsonify({'error': 'Failed to update settings.'}), 500
    # Load existing settings for GET request
    try:
        with open('/home/choco/chocomap/config/app_settings.json', 'r') as f:
            app_settings = json.load(f)
        with open('/home/choco/chocomap/config/email_settings.json', 'r') as f:
            email_settings = json.load(f)
        with open('/home/choco/chocomap/config/api_keys.json', 'r') as f:
            api_keys = json.load(f)
        return jsonify({
            'application': app_settings,
            'email': email_settings,
            'api_keys': api_keys
        })
    except Exception as e:
        current_app.logger.error(f"Error loading settings: {str(e)}")
        return jsonify({'error': 'Failed to load settings.'}), 500
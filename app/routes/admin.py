from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify
from app.models.users import User
from app.middleware import login_required, role_required, rate_limit_by_ip
from app.utils import validate_email, sanitize_input
from app.services.user_service import UserService
from datetime import datetime, date, timedelta
from app import mysql
import logging

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
        flash("Error loading dashboard", "danger")
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
        flash("Error loading users", "danger")
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
        flash("Error loading pending users", "danger")
        return render_template('admin/pending_users.html', users=[])

@admin_bp.route('/approve/<int:user_id>', methods=['POST'])
@login_required
@role_required('admin')
def approve_user(user_id):
    """Approve a user registration"""
    try:
        UserService.update_user(user_id, status='active', approval_status='approved')
        flash("User approved successfully", "success")
    except Exception as e:
        logger.error(f"Error approving user: {str(e)}", exc_info=True)
        flash("Error approving user", "danger")
    
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@login_required
@role_required('admin')
def reject_user(user_id):
    try:
        UserService.update_user(user_id, status='inactive', approval_status='rejected')
        flash("User rejected successfully", "success")
    except Exception as e:
        logger.error(f"Error rejecting user: {str(e)}", exc_info=True)
        flash("Error rejecting user", "danger")
    
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
            flash('User not found', 'danger')
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
            role = request.form.get('role', '')
            active = 'active' in request.form  # Checkbox
            approval_status = request.form.get('approval_status', '')
            
            if not all([name, email, role, approval_status]):
                flash('All fields are required', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
                
            if not validate_email(email):
                flash('Invalid email format', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
            
            # Update user
            if UserService.update_user(user_id, name=name, email=email, role=role, 
                                      active=active, approval_status=approval_status):
                flash('User updated successfully', 'success')
                return redirect(url_for('admin.users'))
            else:
                flash('Error updating user', 'danger')
                return redirect(url_for('admin.edit_user', user_id=user_id))
                
        cursor.close()
        return render_template('admin/edit_user.html', user=user)
        
    except Exception as e:
        logger.error(f"Error editing user: {str(e)}", exc_info=True)
        flash("Error editing user", "danger")
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
            flash('User deleted successfully', 'success')
        else:
            flash('User not found', 'danger')
            
    except Exception as e:
        mysql.connection.rollback()
        logger.error(f"Error deleting user: {str(e)}", exc_info=True)
        flash('Error deleting user', 'danger')
        
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
            flash("User not found", "danger")
            return redirect(url_for('admin.users'))
        
        # Set session to impersonated user
        session['user_id'] = user[0]
        session['name'] = user[1]
        session['user_role'] = user[3]
        session['is_impersonating'] = True
        
        flash(f"You are now impersonating {user[1]}", "warning")
        
        # Redirect to appropriate dashboard
        if user[3] == 'manager':
            return redirect(url_for('manager.dashboard'))
        elif user[3] == 'driver':
            return redirect(url_for('driver.dashboard'))
        else:
            return redirect(url_for('employee.dashboard'))
            
    except Exception as e:
        logger.error(f"Error impersonating user: {str(e)}", exc_info=True)
        flash("Error impersonating user", "danger")
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
        
        flash("Returned to admin account", "info")
    
    return redirect(url_for('admin.dashboard')) 
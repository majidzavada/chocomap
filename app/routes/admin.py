from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from app.models.users import User
from app.middleware import admin_required
from app.utils import validate_email, sanitize_input
import logging

logger = logging.getLogger(__name__)
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

@admin_bp.route('/')
@admin_required
def index():
    return render_template('admin/index.html')

@admin_bp.route('/users')
@admin_required
def users():
    users = User.get_all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/users/pending')
@admin_required
def pending_users():
    users = User.get_all_pending()
    return render_template('admin/pending_users.html', users=users)

@admin_bp.route('/users/<int:user_id>/approve', methods=['POST'])
@admin_required
def approve_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin.pending_users'))
        
    if user.update(approval_status='approved'):
        flash('User approved successfully', 'success')
    else:
        flash('Error approving user', 'danger')
        
    return redirect(url_for('admin.pending_users'))

@admin_bp.route('/users/<int:user_id>/reject', methods=['POST'])
@admin_required
def reject_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin.pending_users'))
        
    if user.update(approval_status='rejected'):
        flash('User rejected successfully', 'success')
    else:
        flash('Error rejecting user', 'danger')
        
    return redirect(url_for('admin.pending_users'))

@admin_bp.route('/users/<int:user_id>/edit', methods=['GET', 'POST'])
@admin_required
def edit_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin.users'))
        
    if request.method == 'POST':
        name = sanitize_input(request.form.get('name', ''))
        email = request.form.get('email', '').strip()
        role = request.form.get('role', '')
        
        if not all([name, email, role]):
            flash('All fields are required', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
            
        if not validate_email(email):
            flash('Invalid email format', 'danger')
            return redirect(url_for('admin.edit_user', user_id=user_id))
            
        if user.update(name=name, email=email, role=role):
            flash('User updated successfully', 'success')
            return redirect(url_for('admin.users'))
        else:
            flash('Error updating user', 'danger')
            
    return render_template('admin/edit_user.html', user=user)

@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
@admin_required
def delete_user(user_id):
    user = User.get_by_id(user_id)
    if not user:
        flash('User not found', 'danger')
        return redirect(url_for('admin.users'))
        
    if user.delete():
        flash('User deleted successfully', 'success')
    else:
        flash('Error deleting user', 'danger')
        
    return redirect(url_for('admin.users')) 
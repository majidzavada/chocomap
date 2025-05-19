import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort
from werkzeug.security import check_password_hash
from app import mysql
from app.models.users import get_user_by_email, verify_password, update_user
from app.middleware import rate_limit_by_ip, cache_control
from datetime import datetime
from app.services.user_service import UserService
from app.utils import validate_email, sanitize_input, is_valid_password
import logging

logger = logging.getLogger(__name__)
auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

def generate_csrf_token():
    if '_csrf_token' not in session:
        session['_csrf_token'] = secrets.token_hex(32)
    return session['_csrf_token']

@auth_bp.before_request
def csrf_protect():
    if request.method in ['POST', 'PUT', 'DELETE']:
        token = session.get('_csrf_token')
        if not token or token != request.form.get('_csrf_token'):
            abort(403)

@auth_bp.context_processor
def inject_csrf_token():
    return dict(csrf_token=generate_csrf_token())

@auth_bp.route('/login', methods=['GET', 'POST'])
@rate_limit_by_ip("5 per minute")
@cache_control(max_age=0, private=True)
def login():
    if 'user_id' in session:
        return redirect(url_for('auth.index'))

    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            
            if not email or not password:
                flash("Email and password are required", "danger")
                return redirect(url_for('auth.login'))
            
            if not validate_email(email):
                flash("Invalid email format", "danger")
                return redirect(url_for('auth.login'))
            
            # Attempt login
            user = UserService.authenticate_user(email, password)
            if user:
                session['user_id'] = user['id']
                session['role'] = user['role']
                session['name'] = user['name']
                
                # Track login activity
                UserService.track_user_activity(
                    user['id'],
                    'login',
                    {'ip': request.remote_addr}
                )
                
                flash("Login successful", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Invalid email or password", "danger")
                return redirect(url_for('auth.login'))
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            flash("An error occurred during login", "danger")
            return redirect(url_for('auth.login'))

    return render_template('auth/login.html')

@auth_bp.route('/logout')
def logout():
    if 'user_id' in session:
        # Track logout activity
        UserService.track_user_activity(
            session['user_id'],
            'logout',
            {'ip': request.remote_addr}
        )
        
    session.clear()
    flash("You have been logged out", "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/')
@cache_control(max_age=60, private=False)  # Cache for 1 minute
def index():
    return render_template('index.html')

@auth_bp.route('/lang/<lang_code>')
def set_language(lang_code):
    allowed_languages = {'cs', 'en'}  # Add more as needed
    if lang_code not in allowed_languages:
        abort(400)
        
    session['lang'] = lang_code
    if 'user_id' in session:
        update_user(session['user_id'], preferred_lang=lang_code)
        
    return redirect(request.referrer or url_for('auth.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
@rate_limit_by_ip("3 per hour")
def register():
    if request.method == 'POST':
        try:
            name = sanitize_input(request.form.get('name', ''))
            email = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            # Validate input
            if not all([name, email, password, confirm_password]):
                flash("All fields are required", "danger")
                return redirect(url_for('auth.register'))
                
            if not validate_email(email):
                flash("Invalid email format", "danger")
                return redirect(url_for('auth.register'))
                
            if password != confirm_password:
                flash("Passwords do not match", "danger")
                return redirect(url_for('auth.register'))
                
            # Validate password strength
            is_valid, message = is_valid_password(password)
            if not is_valid:
                flash(message, "danger")
                return redirect(url_for('auth.register'))
            
            # Create user
            user_id = UserService.create_user(
                name=name,
                email=email,
                password=password,
                role='driver'  # Default role
            )
            
            if user_id:
                flash("Registration successful. Please login.", "success")
                return redirect(url_for('auth.login'))
            else:
                flash("Error creating account", "danger")
                return redirect(url_for('auth.register'))
                
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            flash("An error occurred during registration", "danger")
            return redirect(url_for('auth.register'))
            
    return render_template('auth/register.html')

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@rate_limit_by_ip("3 per hour")
def reset_password():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            
            if not email or not validate_email(email):
                flash("Please enter a valid email address", "danger")
                return redirect(url_for('auth.reset_password'))
            
            # Send password reset email
            if UserService.send_password_reset_email(email):
                flash("Password reset instructions have been sent to your email", "success")
            else:
                flash("Error sending password reset email", "danger")
                
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            flash("An error occurred while processing your request", "danger")
            return redirect(url_for('auth.reset_password'))
            
    return render_template('auth/reset_password.html')

@auth_bp.route('/change-password', methods=['GET', 'POST'])
def change_password():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
        
    if request.method == 'POST':
        try:
            current_password = request.form.get('current_password', '')
            new_password = request.form.get('new_password', '')
            confirm_password = request.form.get('confirm_password', '')
            
            if not all([current_password, new_password, confirm_password]):
                flash("All fields are required", "danger")
                return redirect(url_for('auth.change_password'))
                
            if new_password != confirm_password:
                flash("New passwords do not match", "danger")
                return redirect(url_for('auth.change_password'))
                
            # Validate password strength
            is_valid, message = is_valid_password(new_password)
            if not is_valid:
                flash(message, "danger")
                return redirect(url_for('auth.change_password'))
            
            # Change password
            if UserService.change_password(
                user_id=session['user_id'],
                current_password=current_password,
                new_password=new_password
            ):
                flash("Password changed successfully", "success")
                return redirect(url_for('dashboard'))
            else:
                flash("Current password is incorrect", "danger")
                return redirect(url_for('auth.change_password'))
                
        except Exception as e:
            logger.error(f"Password change error: {str(e)}")
            flash("An error occurred while changing your password", "danger")
            return redirect(url_for('auth.change_password'))
            
    return render_template('auth/change_password.html')

@auth_bp.errorhandler(403)
def forbidden_error(error):
    flash("Access forbidden. Please try again.", "danger")
    return redirect(url_for('auth.login'))

@auth_bp.errorhandler(429)
def ratelimit_error(error):
    flash("Too many attempts. Please try again later.", "danger")
    return render_template('auth/login.html'), 429

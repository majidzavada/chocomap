import secrets
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, abort, jsonify
from flask_babel import _
# from werkzeug.security import check_password_hash
from app import mysql
# from app.models.users import get_user_by_email, verify_password, update_user
from app.middleware import rate_limit_by_ip, cache_control
from datetime import datetime
from app.services.user_service import UserService
from app.utils import validate_email, sanitize_input, is_valid_password
import logging
from flask import current_app

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
            login_input = request.form.get('email', '').strip()
            password = request.form.get('password', '')
            logger.info(f"Login attempt for: {login_input} from IP: {request.remote_addr}")
            if not login_input or not password:
                logger.warning(f"Login failed: missing credentials for {login_input} from {request.remote_addr}")
                flash(_("Email/Username and password are required"), "danger")
                return redirect(url_for('auth.login'))
            # Attempt login
            user = UserService.authenticate_user(login_input, password)
            if user:
                logger.info(f"Successful login for user: {user['id']} ({user['email']})")
                session['user_id'] = user['id']
                session['user_role'] = user['role']
                session['role'] = user['role']
                session['name'] = user['name']
                # Track login activity
                UserService.track_user_activity(
                    user['id'],
                    'login',
                    {'ip': request.remote_addr}
                )
                flash(_("Login successful"), "success")
                # Redirect to the appropriate dashboard based on user role
                if user['role'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif user['role'] == 'manager':
                    return redirect(url_for('manager.dashboard'))
                elif user['role'] == 'driver':
                    return redirect(url_for('driver.dashboard'))
                else:
                    return redirect(url_for('employee.dashboard'))
            else:
                logger.warning(f"Failed login attempt for: {login_input} from {request.remote_addr}")
                flash(_("Invalid email/username or password"), "danger")
                return redirect(url_for('auth.login'))
        except Exception as e:
            logger.error(f"Login error: {str(e)}", exc_info=True)
            flash(_("An error occurred during login. Please try again."), "danger")
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
    flash(_("You have been logged out"), "info")
    return redirect(url_for('auth.login'))

@auth_bp.route('/')
@cache_control(max_age=60, private=False)  # Cache for 1 minute
def index():
    if 'user_id' not in session:
        return redirect(url_for('auth.login'))
    return render_template('index.html')

@auth_bp.route('/home')
@cache_control(max_age=60, private=False)  # Cache for 1 minute
def home():
    return redirect(url_for('auth.index'))

@auth_bp.route('/lang/<lang_code>')
def lang(lang_code):
    """Switch language"""
    if lang_code not in ['en', 'cs']:
        lang_code = 'en'
    
    # Set language in session
    session['lang'] = lang_code
    
    # If user is logged in, update their preferred language
    if 'user_id' in session:
        try:
            cursor = mysql.connection.cursor()
            cursor.execute(
                'UPDATE users SET preferred_lang = %s WHERE id = %s',
                (lang_code, session['user_id'])
            )
            mysql.connection.commit()
            cursor.close()
        except Exception as e:
            logger.error(f"Error updating user language: {str(e)}")
    
    # Redirect back to the previous page or home
    return redirect(request.referrer or url_for('auth.index'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Public self-registration is disabled. Redirect to login."""
    flash(_("Registration is currently disabled. Please contact the administrator."), "warning")
    return redirect(url_for('auth.login'))

@auth_bp.route('/reset-password', methods=['GET', 'POST'])
@rate_limit_by_ip("3 per hour")
def reset_password():
    if request.method == 'POST':
        try:
            email = request.form.get('email', '').strip()
            if not email or not validate_email(email):
                logger.warning(f"Password reset failed: invalid email '{email}' from {request.remote_addr}")
                flash(_("Please enter a valid email address"), "danger")
                return redirect(url_for('auth.reset_password'))
            # Send password reset email
            try:
                sent = UserService.send_password_reset_email(email)
            except Exception as mail_err:
                logger.error(f"Error sending password reset email: {mail_err}")
                flash(_("Error sending password reset email"), "danger")
                return redirect(url_for('auth.reset_password'))
            if sent:
                logger.info(f"Password reset email sent to {email}")
                flash(_("Password reset instructions have been sent to your email"), "success")
            else:
                logger.warning(f"Password reset failed: user not found or error for {email}")
                flash(_("Error sending password reset email"), "danger")
            return redirect(url_for('auth.login'))
        except Exception as e:
            logger.error(f"Password reset error: {str(e)}")
            flash(_("An error occurred while processing your request"), "danger")
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
                flash(_("All fields are required"), "danger")
                return redirect(url_for('auth.change_password'))
            if new_password != confirm_password:
                flash(_("New passwords do not match"), "danger")
                return redirect(url_for('auth.change_password'))
                
            # Validate password strength
            is_valid, message = is_valid_password(new_password)
            if not is_valid:
                flash(_(message), "danger")
                return redirect(url_for('auth.change_password'))
            
            # Change password
            if UserService.change_password(
                user_id=session['user_id'],
                current_password=current_password,
                new_password=new_password
            ):
                flash(_("Password changed successfully"), "success")
                # Redirect to appropriate dashboard based on user role
                if session['user_role'] == 'admin':
                    return redirect(url_for('admin.dashboard'))
                elif session['user_role'] == 'manager':
                    return redirect(url_for('manager.dashboard'))
                elif session['user_role'] == 'driver':
                    return redirect(url_for('driver.dashboard'))
                else:
                    return redirect(url_for('employee.dashboard'))
            else:
                flash(_("Current password is incorrect"), "danger")
                return redirect(url_for('auth.change_password'))
                
        except Exception as e:
            logger.error(f"Password change error: {str(e)}")
            flash(_("An error occurred while changing your password"), "danger")
            return redirect(url_for('auth.change_password'))
            
    return render_template('auth/change_password.html')

@auth_bp.errorhandler(403)
def forbidden_error(error):
    flash(_("Access forbidden. Please try again."), "danger")
    return redirect(url_for('auth.login'))

@auth_bp.errorhandler(429)
def ratelimit_error(error):
    flash(_("Too many attempts. Please try again later."), "danger")
    return render_template('auth/login.html'), 429

@auth_bp.route('/debug/login-status')
def debug_login_status():
    """Debug endpoint to check login status and session info"""
    if not current_app.debug:
        abort(404)
        
    debug_info = {
        'session': dict(session),
        'cookies': dict(request.cookies),
        'headers': dict(request.headers),
        'remote_addr': request.remote_addr,
        'rate_limit_info': {
            'login_limit': '5 per minute',
            'register_limit': '3 per hour',
            'reset_limit': '3 per hour'
        }
    }
    
    return jsonify(debug_info)

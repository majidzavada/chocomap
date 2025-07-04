import os
import logging
from logging.handlers import RotatingFileHandler

# Load environment variables first, before any other imports
from dotenv import load_dotenv
load_dotenv()

from flask import Flask, session, request, render_template, redirect, url_for, current_app, jsonify
from flask_talisman import Talisman
from flask_compress import Compress
from app.config import Config
from app.extensions import (
    db, migrate, cors, limiter, cache, mail, babel, mysql
)
from datetime import datetime

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Explicitly set MySQL config from environment variables
    app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
    app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'root')
    app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', '')
    app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'chocomap')
    app.config['MYSQL_PORT'] = int(os.environ.get('MYSQL_PORT', 3306))
    
    # Debug: Print MySQL config (excluding password)
    print(f"[DEBUG] MySQL config: host={app.config['MYSQL_HOST']}, user={app.config['MYSQL_USER']}, db={app.config['MYSQL_DB']}, port={app.config['MYSQL_PORT']}, password={'set' if app.config['MYSQL_PASSWORD'] else 'NOT SET'}")
    
    # Debug: Print MySQL password (masked)
    pw = app.config['MYSQL_PASSWORD']
    if pw:
        pw_masked = pw[:2] + '*'*(len(pw)-4) + pw[-2:] if len(pw) > 4 else '*'*len(pw)
    else:
        pw_masked = 'NOT SET'
    print(f"[DEBUG] MySQL password: {pw_masked}")
    
    # Initialize extensions
    mysql.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    
    # Initialize rate limiter
    limiter.init_app(app)
    
    cache.init_app(app)
    mail.init_app(app)
    
    # Debug: Log MySQL config (excluding password)
    app.logger.info(f"MySQL config: host={app.config['MYSQL_HOST']}, user={app.config['MYSQL_USER']}, db={app.config['MYSQL_DB']}, port={app.config['MYSQL_PORT']}")
    
    # Define locale selector function
    def get_locale():
        """Get the locale for the current request"""
        # First try to get language from session
        if 'lang' in session:
            return session['lang']
        
        # Then try to get from user preferences if logged in
        if 'user_id' in session:
            # Attempt to read language preference from database
            try:
                conn = mysql.connection
                cursor = conn.cursor()
                cursor.execute('SELECT preferred_lang FROM users WHERE id = %s', (session['user_id'],))
                result = cursor.fetchone()
                cursor.close()
                if result and result[0]:
                    return result[0]
            except Exception as db_err:
                current_app.logger.error(f"Database error fetching user language: {db_err}")
            # If any DB error occurs we silently fall back to default detection
        
        # Finally, try to get from browser settings
        return request.accept_languages.best_match(['en', 'cs'])
    
    # Initialize Babel with the locale selector
    babel.init_app(app, locale_selector=get_locale)
    
    # Make get_locale available in templates
    app.jinja_env.globals.update(get_locale=get_locale)
    
    # Make utility functions available in templates
    from app.utils import get_google_maps_api_key, get_warehouse_location
    app.jinja_env.globals.update(
        get_google_maps_api_key=get_google_maps_api_key,
        get_warehouse_location=get_warehouse_location
    )
    
    # Add custom Jinja filters
    @app.template_filter('date')
    def date_filter(value, format='%Y-%m-%d'):
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except ValueError:
                try:
                    value = datetime.strptime(value, '%Y-%m-%d')
                except ValueError:
                    return value
        if isinstance(value, datetime):
            return value.strftime(format)
        return value
    
    # Set up logging
    if not app.debug and not app.testing:
        if not os.path.exists('logs'):
            os.mkdir('logs')
        file_handler = RotatingFileHandler(
            'logs/chocomap.log',
            maxBytes=10240000,
            backupCount=10
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s: %(message)s '
            '[in %(pathname)s:%(lineno)d]'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)
        
        app.logger.setLevel(logging.INFO)
        app.logger.info('Chocomap startup')
    
    # Register blueprints
    from app.routes.auth import auth_bp
    from app.routes.employee import employee_bp
    from app.routes.driver import driver_bp
    from app.routes.manager import manager_bp
    from app.routes.admin import admin_bp
    
    # Add favicon route
    @app.route('/favicon.ico')
    def favicon():
        return app.send_static_file('favicon.ico')
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(manager_bp)
    app.register_blueprint(admin_bp)
    
    # Register error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        return render_template('errors/500.html'), 500
    
    @app.errorhandler(403)
    def forbidden_error(error):
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(429)
    def ratelimit_error(error):
        return render_template('errors/429.html'), 429
    
    # Add root route
    @app.route('/')
    def root():
        """Root endpoint that shows basic app info"""
        # Serve JSON when explicitly requested, otherwise show the public landing page
        if request.headers.get('Accept') == 'application/json':
            return jsonify({
                'status': 'ok',
                'message': 'Chocomap API is running',
                'version': '1.0.0',
                'endpoints': {
                    'health': url_for('health_check', _external=True),
                    'login': url_for('auth.login', _external=True),
                    'register': url_for('auth.register', _external=True)
                }
            })
        # Render the landing page which handles redirecting/logged-in users itself
        return render_template('index.html')
    
    # Register before_request handlers
    @app.before_request
    def before_request():
        """Execute before each request."""
        # Set language
        if 'lang' in session:
            babel.locale = session['lang']
        
        # Track user activity
        if 'user_id' in session:
            from app.utils import log_activity
            log_activity(
                session['user_id'],
                'page_view',
                {'path': request.path}
            )
    
    # Register after_request handlers
    @app.after_request
    def after_request(response):
        """Execute after each request."""
        # Add security headers
        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'
        response.headers['X-XSS-Protection'] = '1; mode=block'
        if app.config.get('STRICT_TRANSPORT_SECURITY'):
            response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains'
        
        return response
    
    # Register shell context
    @app.shell_context_processor
    def make_shell_context():
        from app.models.users import User
        from app.models.deliveries import Delivery
        from app.models.addresses import Address
        return {
            'db': db,
            'User': User,
            'Delivery': Delivery,
            'Address': Address
        }
    
    # Register CLI commands
    @app.cli.command()
    def test():
        """Run the unit tests."""
        import unittest
        tests = unittest.TestLoader().discover('tests')
        unittest.TextTestRunner(verbosity=2).run(tests)
    
    @app.cli.command()
    def init_db():
        """Initialize the database."""
        db.create_all()
        print('Initialized the database.')
    
    @app.cli.command()
    def create_admin():
        """Create an admin user."""
        from app.services.user_service import UserService
        email = input('Enter admin email: ')
        password = input('Enter admin password: ')
        
        if UserService.create_user(
            name='Admin',
            email=email,
            password=password,
            role='manager'
        ):
            print('Admin user created successfully.')
        else:
            print('Error creating admin user.')
    
    # Add health check route
    @app.route('/health', methods=['GET'])
    def health_check():
        """Health check endpoint"""
        try:
            # Check database connection
            mysql.connection.ping(reconnect=True)
            db_status = 'healthy'
        except Exception as e:
            app.logger.error(f"Database health check failed: {str(e)}")
            db_status = 'unhealthy'
            
        health_info = {
            'status': 'ok',
            'timestamp': datetime.utcnow().isoformat(),
            'database': db_status,
            'debug': app.debug,
            'environment': app.config.get('ENV', 'production'),
            'version': '1.0.0',
            'endpoints': {
                'login': url_for('auth.login', _external=True),
                'register': url_for('auth.register', _external=True),
                'health': url_for('health_check', _external=True)
            }
        }
        
        return jsonify(health_info), 200
    
    return app

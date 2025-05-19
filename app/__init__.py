import os
import logging
from logging.handlers import RotatingFileHandler
from flask import Flask, session, request, render_template
from flask_talisman import Talisman
from flask_compress import Compress
from dotenv import load_dotenv
from app.config import Config
from app.extensions import (
    db, migrate, cors, limiter, cache, mail, babel, mysql
)

def create_app(config_class=Config):
    """Create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    # Initialize extensions
    mysql.init_app(app)
    db.init_app(app)
    migrate.init_app(app, db)
    cors.init_app(app)
    limiter.init_app(app)
    cache.init_app(app)
    mail.init_app(app)
    babel.init_app(app)
    
    # Set up Babel locale selector
    @babel.select_locale
    def get_locale():
        # Try to get the language from the session
        if 'lang' in session:
            return session['lang']
        # Otherwise try to guess the language from the user accept
        # header the browser transmits
        return request.accept_languages.best_match(['en', 'cs'])
    
    # Make get_locale available in templates
    app.jinja_env.globals.update(get_locale=get_locale)
    
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
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(manager_bp)
    
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
    
    return app

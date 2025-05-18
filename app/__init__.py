import os
from flask import Flask, session
from flask_mysqldb import MySQL
from flask_babel import Babel
from dotenv import load_dotenv
from app.config import Config

mysql = MySQL()
babel = Babel()

def create_app():
    # Load environment variables first
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)

    # Initialize MySQL
    mysql.init_app(app)

    # Define locale selector function for Babel
    def get_locale():
        return session.get('lang', 'cz')

    # Initialize Babel with selector
    babel.init_app(app, locale_selector=get_locale)

    # Inject get_locale into templates
    @app.context_processor
    def inject_get_locale():
        return dict(get_locale=get_locale)

    # Register blueprints
    from .routes.auth import auth_bp
    from .routes.driver import driver_bp
    from .routes.employee import employee_bp
    from .routes.manager import manager_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(manager_bp)

    return app

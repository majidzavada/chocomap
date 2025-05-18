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

    # Initialize MySQL as before
    mysql.init_app(app)

    # Define your locale selector function
    def get_locale():
        return session.get('lang', 'cz')

    # Initialize Babel with your selector (no decorator)
    babel.init_app(app, locale_selector=get_locale)  # ← new API

    # Register your blueprints
    from .routes.auth import auth_bp
    from .routes.driver import driver_bp
    from .routes.employee import employee_bp
    from .routes.manager import manager_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(manager_bp)

    return app

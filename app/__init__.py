import os
from flask import Flask, session
from flask_mysqldb import MySQL
from flask_babel import Babel
from dotenv import load_dotenv
from app.config import Config  # ← Use the new config class

mysql = MySQL()
babel = Babel()

def create_app():
    load_dotenv()

    app = Flask(__name__)
    app.config.from_object(Config)  # ← Load config from class

    mysql.init_app(app)
    babel.init_app(app)

    @babel.locale_selector
    def get_locale():
        return session.get('lang', 'cz')

    from .routes.auth import auth_bp
    from .routes.driver import driver_bp
    from .routes.employee import employee_bp
    from .routes.manager import manager_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(driver_bp)
    app.register_blueprint(employee_bp)
    app.register_blueprint(manager_bp)

    return app

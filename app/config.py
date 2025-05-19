import os
from datetime import timedelta
from typing import Dict, Any

class Config:
    # Basic Flask configuration
    SECRET_KEY = os.environ.get('SECRET_KEY', 'your-secret-key-here')
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() == 'true'
    TESTING = os.environ.get('FLASK_TESTING', 'False').lower() == 'true'
    
    # Database configuration
    MYSQL_HOST = os.environ.get('MYSQL_HOST', 'localhost')
    MYSQL_USER = os.environ.get('MYSQL_USER', 'root')
    MYSQL_PASSWORD = os.environ.get('MYSQL_PASSWORD', '')
    MYSQL_DB = os.environ.get('MYSQL_DB', 'chocomap')
    MYSQL_PORT = int(os.environ.get('MYSQL_PORT', 3306))
    
    # Session configuration
    SESSION_TYPE = 'filesystem'
    PERMANENT_SESSION_LIFETIME = timedelta(days=1)
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    
    # Security configuration
    JWT_SECRET_KEY = os.environ.get('JWT_SECRET_KEY', SECRET_KEY)
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=1)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=30)
    JWT_ALGORITHM = 'HS256'
    
    # Rate limiting
    RATELIMIT_DEFAULT = "200 per day"
    RATELIMIT_STORAGE_URL = os.environ.get('REDIS_URL', 'memory://')
    RATELIMIT_STRATEGY = 'fixed-window'
    
    # Caching
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_DEFAULT_TIMEOUT = 300
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # File upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf'}
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
    MAIL_PORT = int(os.environ.get('MAIL_PORT', 587))
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Google Maps API
    GOOGLE_MAPS_API_KEY = os.environ.get('GOOGLE_MAPS_API_KEY')
    
    # CORS configuration
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', '*').split(',')
    CORS_METHODS = ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS']
    CORS_HEADERS = ['Content-Type', 'Authorization']
    
    # Application specific
    APP_NAME = 'Chocomap'
    APP_VERSION = '1.0.0'
    TIMEZONE = os.environ.get('TIMEZONE', 'UTC')
    DEFAULT_LANGUAGE = os.environ.get('DEFAULT_LANGUAGE', 'en')
    
    # Feature flags
    ENABLE_ANALYTICS = os.environ.get('ENABLE_ANALYTICS', 'True').lower() == 'true'
    ENABLE_NOTIFICATIONS = os.environ.get('ENABLE_NOTIFICATIONS', 'True').lower() == 'true'
    ENABLE_FILE_UPLOAD = os.environ.get('ENABLE_FILE_UPLOAD', 'True').lower() == 'true'
    
    @classmethod
    def get_config(cls) -> Dict[str, Any]:
        """Get all configuration values as a dictionary."""
        return {key: value for key, value in cls.__dict__.items()
                if not key.startswith('_') and isinstance(value, (str, int, float, bool, list, dict))}
    
    @classmethod
    def init_app(cls, app) -> None:
        """Initialize application with configuration."""
        # Set up logging
        import logging
        from logging.handlers import RotatingFileHandler
        
        handler = RotatingFileHandler(
            cls.LOG_FILE,
            maxBytes=10000000,  # 10MB
            backupCount=5
        )
        handler.setFormatter(logging.Formatter(cls.LOG_FORMAT))
        app.logger.addHandler(handler)
        app.logger.setLevel(getattr(logging, cls.LOG_LEVEL))
        
        # Create upload folder if it doesn't exist
        if cls.ENABLE_FILE_UPLOAD:
            os.makedirs(cls.UPLOAD_FOLDER, exist_ok=True)
        
        # Set up CORS
        if hasattr(app, 'extensions') and 'cors' in app.extensions:
            app.extensions['cors'].init_app(app)
        
        # Set up caching
        if hasattr(app, 'extensions') and 'cache' in app.extensions:
            app.extensions['cache'].init_app(app)
        
        # Set up rate limiting
        if hasattr(app, 'extensions') and 'limiter' in app.extensions:
            app.extensions['limiter'].init_app(app)
        
        # Set up email
        if hasattr(app, 'extensions') and 'mail' in app.extensions:
            app.extensions['mail'].init_app(app)

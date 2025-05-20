from flask_mysqldb import MySQL
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from flask_mail import Mail
from flask_babel import Babel

# Initialize extensions
mysql = MySQL()
db = SQLAlchemy()
migrate = Migrate()
cors = CORS()
limiter = Limiter(
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour", "10 per minute"],
    storage_uri="redis://localhost:6379/0",
    strategy="fixed-window"
)
cache = Cache()
mail = Mail()
babel = Babel() 
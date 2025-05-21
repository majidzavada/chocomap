import re
from datetime import datetime, timezone
from functools import wraps
import hashlib
from typing import Optional, Any, Dict, List
import json
import secrets
import logging
from flask import request, jsonify
import jwt
from app.config import Config
import bcrypt

logger = logging.getLogger(__name__)

def sanitize_input(input_str: str) -> str:
    """Sanitize user input to prevent XSS attacks."""
    if not input_str:
        return ""
    # Remove HTML tags and special characters
    return re.sub(r'[<>]', '', input_str)

def validate_email(email: str) -> bool:
    """Validate email format."""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return bool(re.match(pattern, email))

def validate_password(password: str) -> bool:
    """Validate password strength."""
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True

def hash_password(password: str) -> str:
    """Hash password using bcrypt."""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    """Verify password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False

def format_datetime(dt: Optional[datetime], format_str: str = '%Y-%m-%d %H:%M:%S') -> str:
    """Format datetime object to string"""
    if not dt:
        return ""
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.strftime(format_str)

def parse_datetime(dt_str: str) -> Optional[datetime]:
    """Parse datetime string to datetime object"""
    formats = [
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d',
        '%Y-%m-%dT%H:%M:%S',
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%dT%H:%M:%SZ'
    ]
    
    for fmt in formats:
        try:
            return datetime.strptime(dt_str, fmt)
        except ValueError:
            continue
    return None

def generate_hash(data: Any) -> str:
    """Generate a hash from any data type"""
    if isinstance(data, (dict, list)):
        data = json.dumps(data, sort_keys=True)
    return hashlib.sha256(str(data).encode()).hexdigest()

def paginate(items: List[Any], page: int, per_page: int) -> Dict[str, Any]:
    """Paginate a list of items"""
    total = len(items)
    pages = (total + per_page - 1) // per_page
    page = min(max(page, 1), pages)
    
    start = (page - 1) * per_page
    end = start + per_page
    
    return {
        'items': items[start:end],
        'page': page,
        'per_page': per_page,
        'total': total,
        'pages': pages,
        'has_prev': page > 1,
        'has_next': page < pages
    }

def memoize(timeout: int = 300):
    """Memoize a function result with timeout"""
    cache = {}
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            now = datetime.now().timestamp()
            
            if key in cache:
                result, timestamp = cache[key]
                if now - timestamp < timeout:
                    return result
            
            result = func(*args, **kwargs)
            cache[key] = (result, now)
            return result
        return wrapper
    return decorator

def format_file_size(size: int) -> str:
    """Format file size to human readable format"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} PB"

def truncate_string(text: str, length: int = 100, suffix: str = '...') -> str:
    """Truncate string to specified length"""
    if len(text) <= length:
        return text
    return text[:length].rsplit(' ', 1)[0] + suffix

def is_valid_password(password: str) -> tuple[bool, str]:
    """
    Validate password strength
    Returns: (is_valid, message)
    """
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    return True, "Password is valid"

def generate_token(user_id: int, role: str) -> str:
    """Generate JWT token."""
    payload = {
        'user_id': user_id,
        'role': role,
        'exp': datetime.utcnow() + Config.JWT_EXPIRATION_DELTA
    }
    return jwt.encode(payload, Config.SECRET_KEY, algorithm='HS256')

def verify_token(token: str) -> Optional[Dict[str, Any]]:
    """Verify JWT token."""
    try:
        payload = jwt.decode(token, Config.SECRET_KEY, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.InvalidTokenError as e:
        logger.error(f"Invalid token: {str(e)}")
        return None

def rate_limit(limit: int, per: int = 60):
    """Rate limiting decorator."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            # Implement rate limiting logic here
            # This is a placeholder for actual rate limiting implementation
            return f(*args, **kwargs)
        return wrapped
    return decorator

def cache_control(max_age: int = 300):
    """Cache control decorator."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            response = f(*args, **kwargs)
            if isinstance(response, tuple):
                response, status_code = response
            else:
                status_code = 200
            response.headers['Cache-Control'] = f'public, max-age={max_age}'
            return response, status_code
        return wrapped
    return decorator

def handle_api_error(f):
    """API error handling decorator."""
    @wraps(f)
    def wrapped(*args, **kwargs):
        try:
            return f(*args, **kwargs)
        except Exception as e:
            logger.error(f"API error: {str(e)}")
            return jsonify({
                'error': 'Internal server error',
                'message': str(e)
            }), 500
    return wrapped

def validate_request_data(required_fields: list):
    """Request data validation decorator."""
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            data = request.get_json()
            if not data:
                return jsonify({'error': 'No data provided'}), 400
            for field in required_fields:
                if field not in data:
                    return jsonify({'error': f'Missing required field: {field}'}), 400
            return f(*args, **kwargs)
        return wrapped
    return decorator

def format_error_response(error: str, status_code: int = 400) -> tuple:
    """Format error response."""
    return jsonify({'error': error}), status_code

def format_success_response(data: Any = None, message: str = None) -> tuple:
    """Format success response."""
    response = {'success': True}
    if data is not None:
        response['data'] = data
    if message is not None:
        response['message'] = message
    return jsonify(response), 200

def log_activity(user_id: int, action: str, details: Dict[str, Any] = None):
    """Log user activity."""
    try:
        logger.info(f"User {user_id} performed {action}")
        if details:
            logger.debug(f"Activity details: {details}")
    except Exception as e:
        logger.error(f"Error logging activity: {str(e)}")

def validate_coordinates(lat: float, lng: float) -> bool:
    """Validate geographic coordinates."""
    return -90 <= lat <= 90 and -180 <= lng <= 180

def calculate_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Calculate distance between two points using Haversine formula."""
    from math import radians, sin, cos, sqrt, atan2
    
    R = 6371  # Earth's radius in kilometers
    
    lat1, lng1, lat2, lng2 = map(radians, [lat1, lng1, lat2, lng2])
    dlat = lat2 - lat1
    dlng = lng2 - lng1
    
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlng/2)**2
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    distance = R * c
    
    return distance 
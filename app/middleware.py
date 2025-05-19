from functools import wraps
from flask import session, redirect, url_for, request, abort, jsonify
from app.models.users import get_user_by_id
from app.utils import verify_token, log_activity
import logging
from typing import Callable, Any
import time
from app.config import Config

logger = logging.getLogger(__name__)

def login_required(f: Callable) -> Callable:
    """Decorator to require user login."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        if not session.get('user_id'):
            if request.is_json:
                return jsonify({'error': 'Authentication required'}), 401
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function

def role_required(*roles: str) -> Callable:
    """Decorator to require specific user role(s)."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if session.get('role') not in roles:
                if request.is_json:
                    return jsonify({'error': 'Permission denied'}), 403
                return redirect(url_for('auth.login'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def api_auth_required(f: Callable) -> Callable:
    """Decorator to require API authentication."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({'error': 'Authentication required'}), 401
            
        token = auth_header.split(' ')[1]
        payload = verify_token(token)
        if not payload:
            return jsonify({'error': 'Invalid or expired token'}), 401
            
        request.user_id = payload['user_id']
        request.user_role = payload['role']
        return f(*args, **kwargs)
    return decorated_function

def user_loader():
    if 'user_id' in session:
        return get_user_by_id(session['user_id'])
    return None

def check_csrf():
    """CSRF protection for all POST/PUT/DELETE requests"""
    if request.method in ['POST', 'PUT', 'DELETE']:
        token = session.get('_csrf_token')
        if not token or token != request.form.get('_csrf_token'):
            abort(403)

def rate_limit_by_ip(limit_str: str) -> Callable:
    """Decorator to implement rate limiting by IP address."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Parse limit string (e.g., "100 per minute")
            try:
                limit, period = limit_str.split(' per ')
                limit = int(limit)
                period_seconds = {
                    'second': 1,
                    'minute': 60,
                    'hour': 3600,
                    'day': 86400
                }.get(period.lower(), 60)
            except ValueError:
                logger.error(f"Invalid rate limit format: {limit_str}")
                return f(*args, **kwargs)
                
            # Get client IP
            client_ip = request.remote_addr
            
            # Check rate limit
            # This is a placeholder for actual rate limiting implementation
            # You should use Redis or similar for production
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def track_request(f: Callable) -> Callable:
    """Decorator to track request details."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        start_time = time.time()
        
        # Log request details
        logger.info(f"Request: {request.method} {request.path}")
        logger.debug(f"Headers: {dict(request.headers)}")
        if request.is_json:
            logger.debug(f"JSON data: {request.get_json()}")
            
        # Execute the route function
        response = f(*args, **kwargs)
        
        # Calculate request duration
        duration = time.time() - start_time
        logger.info(f"Request completed in {duration:.2f} seconds")
        
        return response
    return decorated_function

def validate_json_schema(schema: dict) -> Callable:
    """Decorator to validate JSON request data against a schema."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            if not request.is_json:
                return jsonify({'error': 'Content-Type must be application/json'}), 400
                
            data = request.get_json()
            errors = []
            
            # Validate required fields
            for field, field_schema in schema.items():
                if field_schema.get('required', False) and field not in data:
                    errors.append(f"Missing required field: {field}")
                elif field in data:
                    # Validate field type
                    field_type = field_schema.get('type')
                    if field_type and not isinstance(data[field], field_type):
                        errors.append(f"Invalid type for field {field}")
                        
                    # Validate field format
                    if field_schema.get('format'):
                        if field_schema['format'] == 'email' and not '@' in str(data[field]):
                            errors.append(f"Invalid email format for field {field}")
                        elif field_schema['format'] == 'date' and not isinstance(data[field], str):
                            errors.append(f"Invalid date format for field {field}")
                            
            if errors:
                return jsonify({'errors': errors}), 400
                
            return f(*args, **kwargs)
        return decorated_function
    return decorator

def handle_cors(f: Callable) -> Callable:
    """Decorator to handle CORS headers."""
    @wraps(f)
    def decorated_function(*args: Any, **kwargs: Any) -> Any:
        response = f(*args, **kwargs)
        
        if isinstance(response, tuple):
            response, status_code = response
        else:
            status_code = 200
            
        # Add CORS headers
        response.headers['Access-Control-Allow-Origin'] = Config.CORS_ORIGINS
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
        
        return response, status_code
    return decorated_function

def cache_response(timeout: int = 300) -> Callable:
    """Decorator to cache response."""
    def decorator(f: Callable) -> Callable:
        @wraps(f)
        def decorated_function(*args: Any, **kwargs: Any) -> Any:
            # Generate cache key
            cache_key = f"{request.path}:{request.query_string.decode()}"
            
            # Check cache
            # This is a placeholder for actual caching implementation
            # You should use Redis or similar for production
            
            response = f(*args, **kwargs)
            
            # Cache response
            # This is a placeholder for actual caching implementation
            
            return response
        return decorated_function
    return decorator

def cache_control(max_age=0, private=True):
    """Decorator to set cache control headers"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            response = f(*args, **kwargs)
            
            # Convert string response to Response object
            if isinstance(response, str):
                from flask import make_response
                response = make_response(response)
            
            # Handle tuple responses (response, status_code)
            if isinstance(response, tuple):
                response, status_code = response
                if isinstance(response, str):
                    from flask import make_response
                    response = make_response(response, status_code)
            
            if private:
                response.headers['Cache-Control'] = f'private, max-age={max_age}'
            else:
                response.headers['Cache-Control'] = f'public, max-age={max_age}'
            return response
        return decorated_function
    return decorator 
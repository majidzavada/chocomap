# from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import mysql
import functools
from flask import current_app
import time
from datetime import datetime
import bcrypt
import logging

logger = logging.getLogger(__name__)

def cache_with_timeout(timeout=300):  # 5 minutes default
    def decorator(f):
        cache = {}
        @functools.wraps(f)
        def wrapper(*args, **kwargs):
            key = str(args) + str(kwargs)
            if key in cache:
                result, timestamp = cache[key]
                if time.time() - timestamp < timeout:
                    return result
            result = f(*args, **kwargs)
            cache[key] = (result, time.time())
            return result
        return wrapper
    return decorator

def get_user_by_email(email):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        return user
    except Exception as e:
        logger.error(f"Error fetching user by email: {str(e)}")
        return None
    finally:
        if cursor:
            cursor.close()

def get_user_by_id(user_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        return user
    except Exception as e:
        logger.error(f"Error fetching user by id: {str(e)}")
        return None
    finally:
        if cursor:
            cursor.close()

@cache_with_timeout(timeout=300)
def get_all_drivers():
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT id, name, email FROM users WHERE role = 'driver' AND active = TRUE ORDER BY name")
        drivers = cursor.fetchall()
        return drivers
    except Exception as e:
        logger.error(f"Error fetching drivers: {str(e)}")
        return []
    finally:
        if cursor:
            cursor.close()

def create_user(name, email, password, role='employee', preferred_lang='cs'):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        password_hash = bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, preferred_lang, active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (name, email, password_hash, role, preferred_lang))
        mysql.connection.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating user: {str(e)}")
        mysql.connection.rollback()
        return None
    finally:
        if cursor:
            cursor.close()

def update_user(user_id, **kwargs):
    allowed_fields = {'name', 'email', 'role', 'preferred_lang', 'status', 'active'}
    update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not update_fields:
        return False
    
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        query = "UPDATE users SET " + ", ".join(f"{k} = %s" for k in update_fields.keys())
        query += " WHERE id = %s"
        values = list(update_fields.values()) + [user_id]
        
        cursor.execute(query, values)
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating user: {str(e)}")
        mysql.connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()

def change_password(user_id, new_password):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        password_hash = bcrypt.hashpw(new_password.encode(), bcrypt.gensalt()).decode()
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                      (password_hash, user_id))
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        mysql.connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()

def verify_password(user_id, password):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if result:
            return bcrypt.checkpw(password.encode(), result[0].encode())
        return False
    except Exception as e:
        logger.error(f"Error verifying password: {str(e)}")
        return False
    finally:
        if cursor:
            cursor.close()

def deactivate_user(user_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE users SET active = FALSE WHERE id = %s", (user_id,))
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deactivating user: {str(e)}")
        mysql.connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()

def get_user_stats(user_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            SELECT 
                COUNT(DISTINCT d.id) as total_deliveries,
                COUNT(DISTINCT CASE WHEN d.status = 'completed' THEN d.id END) as completed_deliveries,
                AVG(CASE WHEN d.status = 'completed' THEN TIMESTAMPDIFF(MINUTE, d.created_at, d.completed_at) END) as avg_delivery_time
            FROM users u
            LEFT JOIN deliveries d ON u.id = d.driver_id
            WHERE u.id = %s
        """, (user_id,))
        return cursor.fetchone()
    except Exception as e:
        logger.error(f"Error fetching user stats: {str(e)}")
        return None
    finally:
        if cursor:
            cursor.close()

class User:
    def __init__(self, id, name, email, role, preferred_lang='en', approval_status='pending', created_at=None):
        self.id = id
        self.name = name
        self.email = email
        self.role = role
        self.preferred_lang = preferred_lang
        self.approval_status = approval_status  # pending, approved, rejected
        self.created_at = created_at or datetime.utcnow()

    @staticmethod
    def get_by_id(user_id):
        cursor = None
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT id, name, email, role, preferred_lang, approval_status, created_at FROM users WHERE id = %s', (user_id,))
            user_tuple = cursor.fetchone()
            
            if not user_tuple:
                return None
                
            # Convert tuple to kwargs for User constructor
            user_data = {
                'id': user_tuple[0],
                'name': user_tuple[1],
                'email': user_tuple[2],
                'role': user_tuple[3],
                'preferred_lang': user_tuple[4],
                'approval_status': user_tuple[5],
                'created_at': user_tuple[6]
            }
            return User(**user_data)
        except Exception as e:
            logger.error(f"Error fetching user by id: {str(e)}")
            return None
        finally:
            if cursor:
                cursor.close()

    @staticmethod
    def get_by_email(email):
        cursor = mysql.connection.cursor()
        cursor.execute('SELECT id, name, email, role, preferred_lang, approval_status, created_at FROM users WHERE email = %s', (email,))
        user_tuple = cursor.fetchone()
        cursor.close()
        
        if not user_tuple:
            return None
            
        # Convert tuple to kwargs for User constructor
        user_data = {
            'id': user_tuple[0],
            'name': user_tuple[1],
            'email': user_tuple[2],
            'role': user_tuple[3],
            'preferred_lang': user_tuple[4],
            'approval_status': user_tuple[5],
            'created_at': user_tuple[6]
        }
        return User(**user_data)

    @staticmethod
    def get_all_pending():
        cursor = None
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT id, name, email, role, preferred_lang, approval_status, created_at FROM users WHERE approval_status = %s', ('pending',))
            users_tuples = cursor.fetchall()
            
            users = []
            for user_tuple in users_tuples:
                user_data = {
                    'id': user_tuple[0],
                    'name': user_tuple[1],
                    'email': user_tuple[2],
                    'role': user_tuple[3],
                    'preferred_lang': user_tuple[4],
                    'approval_status': user_tuple[5],
                    'created_at': user_tuple[6]
                }
                users.append(User(**user_data))
            return users
        except Exception as e:
            logger.error(f"Error fetching pending users: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()

    @staticmethod
    def get_all():
        cursor = None
        try:
            cursor = mysql.connection.cursor()
            cursor.execute('SELECT id, name, email, role, preferred_lang, approval_status, created_at FROM users')
            users_tuples = cursor.fetchall()
            
            users = []
            for user_tuple in users_tuples:
                user_data = {
                    'id': user_tuple[0],
                    'name': user_tuple[1],
                    'email': user_tuple[2],
                    'role': user_tuple[3],
                    'preferred_lang': user_tuple[4],
                    'approval_status': user_tuple[5],
                    'created_at': user_tuple[6]
                }
                users.append(User(**user_data))
            return users
        except Exception as e:
            logger.error(f"Error fetching all users: {str(e)}")
            return []
        finally:
            if cursor:
                cursor.close()

    def update(self, **kwargs):
        allowed_fields = {'name', 'email', 'role', 'preferred_lang', 'approval_status'}
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
            
        set_clause = ', '.join(f'{k} = %s' for k in updates.keys())
        values = list(updates.values())
        values.append(self.id)
        
        cursor = mysql.connection.cursor()
        cursor.execute(f'UPDATE users SET {set_clause} WHERE id = %s', values)
        mysql.connection.commit()
        cursor.close()
        
        for k, v in updates.items():
            setattr(self, k, v)
            
        return True

    def delete(self):
        cursor = mysql.connection.cursor()
        cursor.execute('DELETE FROM users WHERE id = %s', (self.id,))
        mysql.connection.commit()
        cursor.close()
        return True

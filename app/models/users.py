from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import mysql
import functools
from flask import current_app
import time

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
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()

def get_user_by_id(user_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cursor.fetchone()
        return user
    finally:
        cursor.close()

@cache_with_timeout(timeout=300)
def get_all_drivers():
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT id, name, email, status FROM users WHERE role = 'driver' AND active = TRUE")
        drivers = cursor.fetchall()
        return drivers
    finally:
        cursor.close()

def create_user(name, email, password, role='employee', preferred_lang='cs'):
    cursor = mysql.connection.cursor()
    try:
        password_hash = generate_password_hash(password)
        cursor.execute("""
            INSERT INTO users (name, email, password_hash, role, preferred_lang, active)
            VALUES (%s, %s, %s, %s, %s, TRUE)
        """, (name, email, password_hash, role, preferred_lang))
        mysql.connection.commit()
        return cursor.lastrowid
    finally:
        cursor.close()

def update_user(user_id, **kwargs):
    allowed_fields = {'name', 'email', 'role', 'preferred_lang', 'status', 'active'}
    update_fields = {k: v for k, v in kwargs.items() if k in allowed_fields}
    
    if not update_fields:
        return False
    
    cursor = mysql.connection.cursor()
    try:
        query = "UPDATE users SET " + ", ".join(f"{k} = %s" for k in update_fields.keys())
        query += " WHERE id = %s"
        values = list(update_fields.values()) + [user_id]
        
        cursor.execute(query, values)
        mysql.connection.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()

def change_password(user_id, new_password):
    cursor = mysql.connection.cursor()
    try:
        password_hash = generate_password_hash(new_password)
        cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s",
                      (password_hash, user_id))
        mysql.connection.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()

def verify_password(user_id, password):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
        result = cursor.fetchone()
        if result:
            return check_password_hash(result['password_hash'], password)
        return False
    finally:
        cursor.close()

def deactivate_user(user_id):
    cursor = mysql.connection.cursor()
    try:
        cursor.execute("UPDATE users SET active = FALSE WHERE id = %s", (user_id,))
        mysql.connection.commit()
        return cursor.rowcount > 0
    finally:
        cursor.close()

def get_user_stats(user_id):
    cursor = mysql.connection.cursor()
    try:
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
    finally:
        cursor.close()

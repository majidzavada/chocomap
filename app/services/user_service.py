from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from app import mysql
from app.utils import hash_password, is_valid_password, verify_password
import logging

logger = logging.getLogger(__name__)

class UserService:
    @staticmethod
    def create_user(
        name: str,
        email: str,
        password: str,
        role: str
    ) -> Optional[int]:
        """Create a new user with validation"""
        cursor = mysql.connection.cursor()
        try:
            # Validate password
            is_valid, message = is_valid_password(password)
            if not is_valid:
                logger.warning(f"Invalid password: {message}")
                return None

            # Hash password
            password_hash = hash_password(password)
            
            cursor.execute("""
                INSERT INTO users (
                    name, email, password_hash, role,
                    active, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, TRUE, NOW(), NOW())
            """, (name, email, password_hash, role))
            
            mysql.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error creating user: {str(e)}")
            return None
        finally:
            cursor.close()

    @staticmethod
    def update_user(
        user_id: int,
        name: Optional[str] = None,
        email: Optional[str] = None,
        phone: Optional[str] = None,
        role: Optional[str] = None,
        status: Optional[str] = None,
        active: Optional[bool] = None,
        approval_status: Optional[str] = None
    ) -> bool:
        """Update user information"""
        cursor = mysql.connection.cursor()
        try:
            updates = []
            params = []
            
            if name is not None:
                updates.append("name = %s")
                params.append(name)
            if email is not None:
                updates.append("email = %s")
                params.append(email)
            if phone is not None:
                updates.append("phone = %s")
                params.append(phone)
            if role is not None:
                updates.append("role = %s")
                params.append(role)
            if status is not None:
                updates.append("status = %s")
                params.append(status)
            if active is not None:
                updates.append("active = %s")
                params.append(active)
            if approval_status is not None:
                updates.append("approval_status = %s")
                params.append(approval_status)
            
            if not updates:
                return False
                
            updates.append("updated_at = NOW()")
            params.append(user_id)
            
            query = f"""
                UPDATE users 
                SET {', '.join(updates)}
                WHERE id = %s
            """
            
            cursor.execute(query, tuple(params))
            mysql.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error updating user: {str(e)}")
            return False
        finally:
            cursor.close()

    @staticmethod
    def deactivate_user(user_id: int) -> bool:
        """Deactivate a user account"""
        return UserService.update_user(user_id, status='inactive', active=False)

    @staticmethod
    def get_user_stats() -> Dict[str, Any]:
        """Get user statistics"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_users,
                    COUNT(CASE WHEN role = 'driver' THEN 1 END) as total_drivers,
                    COUNT(CASE WHEN role = 'manager' THEN 1 END) as total_managers,
                    COUNT(CASE WHEN active = TRUE THEN 1 END) as active_users
                FROM users
            """)
            result = cursor.fetchone()
            if result:
                return {
                    'total_users': result[0],
                    'total_drivers': result[1],
                    'total_managers': result[2],
                    'active_users': result[3],
                    'active_last_week': 0  # Default value since we don't have last_login data
                }
            return {
                'total_users': 0,
                'total_drivers': 0,
                'total_managers': 0,
                'active_users': 0,
                'active_last_week': 0
            }
        finally:
            cursor.close()

    @staticmethod
    def get_user_activity(user_id: int, days: int = 30) -> List[Dict[str, Any]]:
        """Get user activity for the last N days"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as activity_count,
                    GROUP_CONCAT(DISTINCT role) as roles
                FROM user_activity
                WHERE user_id = %s
                AND created_at >= DATE_SUB(NOW(), INTERVAL %s DAY)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """, (user_id, days))
            result = cursor.fetchall()
            return [
                {
                    'date': row[0],
                    'activity_count': row[1],
                    'roles': row[2]
                }
                for row in result
            ]
        finally:
            cursor.close()

    @staticmethod
    def track_user_activity(user_id: int, action: str, details: Optional[Dict] = None) -> bool:
        """Track user activity"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO user_activity (
                    user_id, action, details, created_at
                ) VALUES (%s, %s, %s, NOW())
            """, (user_id, action, str(details) if details else None))
            mysql.connection.commit()
            return True
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error tracking user activity: {str(e)}")
            return False
        finally:
            cursor.close()

    @staticmethod
    def authenticate_user(login_input: str, password: str) -> Optional[Dict[str, Any]]:
        """Authenticate a user with email or username and password"""
        cursor = mysql.connection.cursor()
        try:
            logger.info(f"Attempting to authenticate user: {login_input}")
            
            cursor.execute("""
                SELECT id, name, email, username, password_hash, role, active, approval_status
                FROM users 
                WHERE email = %s OR username = %s
            """, (login_input, login_input))
            user_tuple = cursor.fetchone()
            
            if not user_tuple:
                logger.warning(f"No user found with email/username: {login_input}")
                return None
            
            # Convert tuple to dictionary
            user = {
                'id': user_tuple[0],
                'name': user_tuple[1],
                'email': user_tuple[2],
                'username': user_tuple[3],
                'password_hash': user_tuple[4],
                'role': user_tuple[5],
                'active': user_tuple[6],
                'approval_status': user_tuple[7]
            }
                
            if not user['active']:
                logger.warning(f"Inactive user attempted login: {login_input}")
                return None
                
            if user['approval_status'] != 'approved':
                logger.warning(f"Unapproved user attempted login: {login_input} (approval_status: {user['approval_status']})")
                return None
            
            if verify_password(password, user['password_hash']):
                logger.info(f"Password verified for user: {user['id']}")
                # Update last login - removed since there's no last_login column
                
                # Remove password_hash from user dict
                user.pop('password_hash', None)
                return user
            else:
                logger.warning(f"Invalid password for user: {login_input}")
                return None
                
        except Exception as e:
            logger.error(f"Error authenticating user: {str(e)}", exc_info=True)
            return None
        finally:
            cursor.close()

    @staticmethod
    def change_password(user_id: int, current_password: str, new_password: str) -> bool:
        """Change user's password after verifying current password"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("SELECT password_hash FROM users WHERE id = %s", (user_id,))
            result = cursor.fetchone()
            if not result:
                return False
                
            password_hash = result[0]  # Access by index instead of key
            if not verify_password(current_password, password_hash):
                return False
                
            new_hash = hash_password(new_password)
            cursor.execute("UPDATE users SET password_hash = %s, updated_at = NOW() WHERE id = %s", (new_hash, user_id))
            mysql.connection.commit()
            return True
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error changing password: {str(e)}")
            return False
        finally:
            cursor.close()
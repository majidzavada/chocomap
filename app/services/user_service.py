from datetime import datetime
from typing import Optional, Dict, Any, List
from app import mysql
from app.utils import generate_hash, is_valid_password
import logging

logger = logging.getLogger(__name__)

class UserService:
    @staticmethod
    def create_user(
        name: str,
        email: str,
        password: str,
        role: str,
        phone: Optional[str] = None
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
            password_hash = generate_hash(password)
            
            cursor.execute("""
                INSERT INTO users (
                    name, email, password_hash, role, phone,
                    active, status, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, TRUE, 'active', NOW(), NOW())
            """, (name, email, password_hash, role, phone))
            
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
        status: Optional[str] = None
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
                    COUNT(CASE WHEN active = TRUE THEN 1 END) as active_users,
                    COUNT(CASE WHEN last_login >= DATE_SUB(NOW(), INTERVAL 7 DAY) THEN 1 END) as active_last_week
                FROM users
            """)
            return cursor.fetchone()
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
            return cursor.fetchall()
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
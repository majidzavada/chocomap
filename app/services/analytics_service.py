from typing import Dict, Any, List
from datetime import datetime, timedelta
from app import mysql
import logging

logger = logging.getLogger(__name__)

class AnalyticsService:
    @staticmethod
    def get_delivery_analytics(start_date: str, end_date: str) -> Dict[str, Any]:
        """Get comprehensive delivery analytics"""
        cursor = mysql.connection.cursor()
        try:
            # Get basic delivery stats
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_deliveries,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_deliveries,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_deliveries,
                    COUNT(CASE WHEN status = 'in_progress' THEN 1 END) as in_progress_deliveries,
                    AVG(CASE 
                        WHEN status = 'completed' 
                        THEN TIMESTAMPDIFF(MINUTE, created_at, updated_at)
                    END) as avg_processing_time,
                    AVG(eta_minutes) as avg_eta
                FROM deliveries
                WHERE delivery_date BETWEEN %s AND %s
            """, (start_date, end_date))
            basic_stats = cursor.fetchone()

            # Get delivery trends by day
            cursor.execute("""
                SELECT 
                    delivery_date,
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled
                FROM deliveries
                WHERE delivery_date BETWEEN %s AND %s
                GROUP BY delivery_date
                ORDER BY delivery_date
            """, (start_date, end_date))
            daily_trends = cursor.fetchall()

            # Get driver performance
            cursor.execute("""
                SELECT 
                    u.name as driver_name,
                    COUNT(*) as total_deliveries,
                    COUNT(CASE WHEN d.status = 'completed' THEN 1 END) as completed_deliveries,
                    AVG(CASE 
                        WHEN d.status = 'completed' 
                        THEN TIMESTAMPDIFF(MINUTE, d.created_at, d.updated_at)
                    END) as avg_processing_time,
                    AVG(d.eta_minutes) as avg_eta
                FROM deliveries d
                JOIN users u ON d.driver_id = u.id
                WHERE d.delivery_date BETWEEN %s AND %s
                GROUP BY d.driver_id, u.name
                ORDER BY completed_deliveries DESC
            """, (start_date, end_date))
            driver_performance = cursor.fetchall()

            # Get address distribution
            cursor.execute("""
                SELECT 
                    a.city,
                    COUNT(*) as delivery_count,
                    COUNT(DISTINCT d.driver_id) as unique_drivers
                FROM deliveries d
                JOIN addresses a ON d.address_id = a.id
                WHERE d.delivery_date BETWEEN %s AND %s
                GROUP BY a.city
                ORDER BY delivery_count DESC
            """, (start_date, end_date))
            address_distribution = cursor.fetchall()

            return {
                'basic_stats': basic_stats,
                'daily_trends': daily_trends,
                'driver_performance': driver_performance,
                'address_distribution': address_distribution
            }
        except Exception as e:
            logger.error(f"Error getting delivery analytics: {str(e)}")
            return {}
        finally:
            cursor.close()

    @staticmethod
    def get_user_analytics() -> Dict[str, Any]:
        """Get comprehensive user analytics"""
        cursor = mysql.connection.cursor()
        try:
            # Get user role distribution
            cursor.execute("""
                SELECT 
                    role,
                    COUNT(*) as count,
                    COUNT(CASE WHEN active = TRUE THEN 1 END) as active_count
                FROM users
                GROUP BY role
            """)
            role_distribution = cursor.fetchall()

            # Get user activity trends
            cursor.execute("""
                SELECT 
                    DATE(created_at) as date,
                    COUNT(*) as activity_count,
                    COUNT(DISTINCT user_id) as unique_users
                FROM user_activity
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 30 DAY)
                GROUP BY DATE(created_at)
                ORDER BY date DESC
            """)
            activity_trends = cursor.fetchall()

            # Get user engagement metrics
            cursor.execute("""
                SELECT 
                    COUNT(DISTINCT user_id) as total_users,
                    COUNT(DISTINCT CASE 
                        WHEN last_login >= DATE_SUB(NOW(), INTERVAL 7 DAY) 
                        THEN user_id 
                    END) as active_last_week,
                    COUNT(DISTINCT CASE 
                        WHEN last_login >= DATE_SUB(NOW(), INTERVAL 30 DAY) 
                        THEN user_id 
                    END) as active_last_month,
                    AVG(TIMESTAMPDIFF(DAY, created_at, last_login)) as avg_days_to_first_login
                FROM users
            """)
            engagement_metrics = cursor.fetchone()

            return {
                'role_distribution': role_distribution,
                'activity_trends': activity_trends,
                'engagement_metrics': engagement_metrics
            }
        except Exception as e:
            logger.error(f"Error getting user analytics: {str(e)}")
            return {}
        finally:
            cursor.close()

    @staticmethod
    def get_system_health() -> Dict[str, Any]:
        """Get system health metrics"""
        cursor = mysql.connection.cursor()
        try:
            # Get database metrics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_deliveries,
                    COUNT(DISTINCT driver_id) as active_drivers,
                    COUNT(DISTINCT address_id) as unique_addresses,
                    MAX(created_at) as last_activity
                FROM deliveries
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            db_metrics = cursor.fetchone()

            # Get error rates
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_errors,
                    COUNT(CASE 
                        WHEN level = 'ERROR' 
                        THEN 1 
                    END) as error_count,
                    COUNT(CASE 
                        WHEN level = 'WARNING' 
                        THEN 1 
                    END) as warning_count
                FROM system_logs
                WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
            """)
            error_metrics = cursor.fetchone()

            return {
                'database_metrics': db_metrics,
                'error_metrics': error_metrics,
                'timestamp': datetime.now().isoformat()
            }
        except Exception as e:
            logger.error(f"Error getting system health: {str(e)}")
            return {}
        finally:
            cursor.close()

    @staticmethod
    def track_system_event(event_type: str, details: Dict[str, Any]) -> bool:
        """Track system events"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                INSERT INTO system_logs (
                    event_type, details, created_at
                ) VALUES (%s, %s, NOW())
            """, (event_type, str(details)))
            mysql.connection.commit()
            return True
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error tracking system event: {str(e)}")
            return False
        finally:
            cursor.close() 
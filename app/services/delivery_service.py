from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from app import mysql
from app.models.addresses import get_address_by_id
from app.utils import format_datetime, parse_datetime
import requests
from requests.exceptions import RequestException
import logging
import os

logger = logging.getLogger(__name__)

class DeliveryService:
    @staticmethod
    def calculate_eta(origin_lat: float, origin_lng: float, dest_lat: float, dest_lng: float) -> Optional[int]:
        """Calculate ETA using Google Maps API"""
        try:
            params = {
                'origins': f"{origin_lat},{origin_lng}",
                'destinations': f"{dest_lat},{dest_lng}",
                'key': os.getenv("GOOGLE_MAPS_API_KEY")
            }
            
            response = requests.get(
                "https://maps.googleapis.com/maps/api/distancematrix/json",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            return data['rows'][0]['elements'][0]['duration']['value'] // 60
        except (RequestException, KeyError, IndexError) as e:
            logger.error(f"Error calculating ETA: {str(e)}")
            return None

    @staticmethod
    def create_delivery(
        driver_id: int,
        address_id: int,
        date: str,
        start_time: str,
        end_time: str,
        assigned_by: int,
        notes: str
    ) -> Optional[int]:
        """Create a new delivery with ETA calculation"""
        cursor = mysql.connection.cursor()
        try:
            # Get address coordinates
            address = get_address_by_id(address_id)
            if not address:
                return None

            # Calculate ETA
            wh_lat = float(os.getenv('WAREHOUSE_LAT'))
            wh_lng = float(os.getenv('WAREHOUSE_LNG'))
            eta = DeliveryService.calculate_eta(
                wh_lat, wh_lng,
                float(address['latitude']),
                float(address['longitude'])
            )

            # Insert delivery
            cursor.execute("""
                INSERT INTO deliveries (
                    driver_id, address_id, delivery_date, start_time, end_time,
                    assigned_by, notes, status, eta_minutes, return_eta_minutes,
                    created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s, NOW(), NOW())
            """, (
                driver_id, address_id, date, start_time, end_time,
                assigned_by, notes, eta, eta
            ))
            
            mysql.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error creating delivery: {str(e)}")
            return None
        finally:
            cursor.close()

    @staticmethod
    def update_delivery_status(delivery_id: int, status: str) -> bool:
        """Update delivery status with validation"""
        valid_statuses = {'pending', 'in_progress', 'completed', 'cancelled'}
        if status not in valid_statuses:
            return False

        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                UPDATE deliveries 
                SET status = %s, updated_at = NOW()
                WHERE id = %s
            """, (status, delivery_id))
            mysql.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error updating delivery status: {str(e)}")
            return False
        finally:
            cursor.close()

    @staticmethod
    def get_driver_deliveries(
        driver_id: int,
        date: Optional[str] = None,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Get deliveries for a driver with optional filters"""
        cursor = mysql.connection.cursor()
        try:
            query = """
                SELECT 
                    d.*,
                    a.label,
                    a.street_address,
                    a.latitude,
                    a.longitude,
                    TIMESTAMPDIFF(MINUTE, d.created_at, d.updated_at) as processing_time
                FROM deliveries d
                JOIN addresses a ON d.address_id = a.id
                WHERE d.driver_id = %s
            """
            params = [driver_id]

            if date:
                query += " AND d.delivery_date = %s"
                params.append(date)
            if status:
                query += " AND d.status = %s"
                params.append(status)

            query += " ORDER BY d.delivery_date, d.start_time"
            
            cursor.execute(query, tuple(params))
            deliveries = cursor.fetchall()
            
            # Format datetime fields
            for delivery in deliveries:
                delivery['created_at'] = format_datetime(delivery['created_at'])
                delivery['updated_at'] = format_datetime(delivery['updated_at'])
                delivery['delivery_date'] = format_datetime(delivery['delivery_date'])
            
            return deliveries
        finally:
            cursor.close()

    @staticmethod
    def get_delivery_stats(start_date: str, end_date: str) -> Dict[str, Any]:
        """Get delivery statistics for a date range"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_deliveries,
                    COUNT(CASE WHEN status = 'completed' THEN 1 END) as completed_deliveries,
                    COUNT(CASE WHEN status = 'cancelled' THEN 1 END) as cancelled_deliveries,
                    AVG(CASE 
                        WHEN status = 'completed' 
                        THEN TIMESTAMPDIFF(MINUTE, created_at, updated_at)
                    END) as avg_processing_time,
                    AVG(eta_minutes) as avg_eta
                FROM deliveries
                WHERE delivery_date BETWEEN %s AND %s
            """, (start_date, end_date))
            
            return cursor.fetchone()
        finally:
            cursor.close()

    @staticmethod
    def optimize_delivery_route(driver_id: int, date: str) -> List[Dict[str, Any]]:
        """Optimize delivery route for a driver on a specific date"""
        cursor = mysql.connection.cursor()
        try:
            # Get all pending deliveries for the driver
            cursor.execute("""
                SELECT 
                    d.*,
                    a.latitude,
                    a.longitude
                FROM deliveries d
                JOIN addresses a ON d.address_id = a.id
                WHERE d.driver_id = %s 
                AND d.delivery_date = %s
                AND d.status = 'pending'
                ORDER BY d.start_time
            """, (driver_id, date))
            
            deliveries = cursor.fetchall()
            
            # Simple optimization: sort by start time and ETA
            optimized = sorted(
                deliveries,
                key=lambda x: (
                    parse_datetime(x['start_time']),
                    x['eta_minutes'] or float('inf')
                )
            )
            
            return optimized
        finally:
            cursor.close() 
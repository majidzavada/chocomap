from app import mysql
import os
import requests
import logging

logger = logging.getLogger(__name__)

def get_deliveries_by_driver(driver_id, date=None):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        if date:
            cursor.execute("""
                SELECT d.*, a.label, a.street_address, a.latitude, a.longitude
                FROM deliveries d
                JOIN addresses a ON d.address_id = a.id
                WHERE d.driver_id = %s AND d.delivery_date = %s
                ORDER BY start_time
            """, (driver_id, date))
        else:
            cursor.execute("""
                SELECT d.*, a.label, a.street_address, a.latitude, a.longitude
                FROM deliveries d
                JOIN addresses a ON d.address_id = a.id
                WHERE d.driver_id = %s
                ORDER BY delivery_date, start_time
            """, (driver_id,))
        result = cursor.fetchall()
        return result
    except Exception as e:
        logger.error(f"Error fetching deliveries for driver {driver_id}: {str(e)}")
        return []
    finally:
        if cursor:
            cursor.close()

def update_delivery_status(delivery_id, status):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("UPDATE deliveries SET status = %s WHERE id = %s", (status, delivery_id))
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error updating delivery status: {str(e)}")
        mysql.connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()

def get_all_deliveries_grouped(driver_filter=None, date_filter=None):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        query = """
            SELECT d.*, u.name AS driver_name, a.label, a.street_address
            FROM deliveries d
            JOIN users u ON d.driver_id = u.id
            JOIN addresses a ON d.address_id = a.id
        """
        conditions = []
        params = []

        if driver_filter:
            conditions.append("u.name = %s")
            params.append(driver_filter)
        if date_filter:
            conditions.append("d.delivery_date = %s")
            params.append(date_filter)

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        query += " ORDER BY d.delivery_date, d.start_time"
        cursor.execute(query, tuple(params))
        deliveries = cursor.fetchall()

        grouped = {}
        for d in deliveries:
            key = (d['delivery_date'], d['driver_name'])
            if key not in grouped:
                grouped[key] = []
            grouped[key].append(d)
        return grouped
    except Exception as e:
        logger.error(f"Error fetching grouped deliveries: {str(e)}")
        return {}
    finally:
        if cursor:
            cursor.close()

def create_delivery(driver_id, address_id, date, start_time, end_time, assigned_by, notes):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("SELECT latitude, longitude FROM addresses WHERE id = %s", (address_id,))
        address = cursor.fetchone()

        if not address:
            logger.warning(f"Address {address_id} not found for delivery creation")
            return None

        dest_lat = address['latitude']
        dest_lng = address['longitude']
        wh_lat = os.getenv('WAREHOUSE_LAT')
        wh_lng = os.getenv('WAREHOUSE_LNG')

        eta = None
        # Only try Google Maps API if we have required data
        if wh_lat and wh_lng and os.getenv("GOOGLE_MAPS_API_KEY"):
            try:
                params = {
                    'origins': f"{wh_lat},{wh_lng}",
                    'destinations': f"{dest_lat},{dest_lng}",
                    'key': os.getenv("GOOGLE_MAPS_API_KEY")
                }

                response = requests.get("https://maps.googleapis.com/maps/api/distancematrix/json", params=params)
                data = response.json()
                eta = data['rows'][0]['elements'][0]['duration']['value'] // 60
            except Exception as e:
                logger.warning(f"Could not calculate ETA: {str(e)}")
                eta = None

        cursor.execute("""
            INSERT INTO deliveries (
                driver_id, address_id, delivery_date, start_time, end_time,
                assigned_by, notes, status, eta_minutes, return_eta_minutes
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)
        """, (driver_id, address_id, date, start_time, end_time,
              assigned_by, notes, eta, eta))

        mysql.connection.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating delivery: {str(e)}")
        mysql.connection.rollback()
        return None
    finally:
        if cursor:
            cursor.close()

def delete_delivery(delivery_id):
    cursor = None
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM deliveries WHERE id = %s", (delivery_id,))
        mysql.connection.commit()
        return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error deleting delivery {delivery_id}: {str(e)}")
        mysql.connection.rollback()
        return False
    finally:
        if cursor:
            cursor.close()

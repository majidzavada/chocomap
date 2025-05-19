from app import mysql
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

def get_all_addresses() -> List[Dict[str, Any]]:
    """Get all addresses with their details."""
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, u.name as created_by_name 
            FROM addresses a 
            LEFT JOIN users u ON a.created_by = u.id 
            ORDER BY a.label
        """)
        addresses = cursor.fetchall()
        cursor.close()
        return addresses
    except Exception as e:
        logger.error(f"Error fetching addresses: {str(e)}")
        return []

def get_address_by_id(address_id: int) -> Optional[Dict[str, Any]]:
    """Get address details by ID."""
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT a.*, u.name as created_by_name 
            FROM addresses a 
            LEFT JOIN users u ON a.created_by = u.id 
            WHERE a.id = %s
        """, (address_id,))
        address = cursor.fetchone()
        cursor.close()
        return address
    except Exception as e:
        logger.error(f"Error fetching address {address_id}: {str(e)}")
        return None

def create_address(label: str, street: str, city: str, zip_code: str, 
                  lat: float, lon: float, user_id: int) -> Optional[int]:
    """Create a new address and return its ID."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            INSERT INTO addresses (
                label, street_address, city, zip_code, 
                latitude, longitude, created_by, created_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """, (label, street, city, zip_code, lat, lon, user_id, datetime.utcnow()))
        mysql.connection.commit()
        address_id = cursor.lastrowid
        cursor.close()
        return address_id
    except Exception as e:
        logger.error(f"Error creating address: {str(e)}")
        mysql.connection.rollback()
        return None

def update_address(address_id: int, label: str, street: str, city: str, 
                  zip_code: str, lat: float, lon: float) -> bool:
    """Update an existing address."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("""
            UPDATE addresses 
            SET label = %s, street_address = %s, city = %s, 
                zip_code = %s, latitude = %s, longitude = %s,
                updated_at = %s
            WHERE id = %s
        """, (label, street, city, zip_code, lat, lon, datetime.utcnow(), address_id))
        mysql.connection.commit()
        success = cursor.rowcount > 0
        cursor.close()
        return success
    except Exception as e:
        logger.error(f"Error updating address {address_id}: {str(e)}")
        mysql.connection.rollback()
        return False

def delete_address(address_id: int) -> bool:
    """Delete an address."""
    try:
        cursor = mysql.connection.cursor()
        cursor.execute("DELETE FROM addresses WHERE id = %s", (address_id,))
        mysql.connection.commit()
        success = cursor.rowcount > 0
        cursor.close()
        return success
    except Exception as e:
        logger.error(f"Error deleting address {address_id}: {str(e)}")
        mysql.connection.rollback()
        return False

def get_addresses_by_user(user_id: int) -> List[Dict[str, Any]]:
    """Get all addresses created by a specific user."""
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT * FROM addresses 
            WHERE created_by = %s 
            ORDER BY created_at DESC
        """, (user_id,))
        addresses = cursor.fetchall()
        cursor.close()
        return addresses
    except Exception as e:
        logger.error(f"Error fetching addresses for user {user_id}: {str(e)}")
        return []

def search_addresses(query: str) -> List[Dict[str, Any]]:
    """Search addresses by label, street, city, or zip code."""
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        search_term = f"%{query}%"
        cursor.execute("""
            SELECT * FROM addresses 
            WHERE label LIKE %s 
               OR street_address LIKE %s 
               OR city LIKE %s 
               OR zip_code LIKE %s
            ORDER BY label
        """, (search_term, search_term, search_term, search_term))
        addresses = cursor.fetchall()
        cursor.close()
        return addresses
    except Exception as e:
        logger.error(f"Error searching addresses: {str(e)}")
        return []

def get_address_stats() -> Dict[str, Any]:
    """Get statistics about addresses."""
    try:
        cursor = mysql.connection.cursor(dictionary=True)
        cursor.execute("""
            SELECT 
                COUNT(*) as total_addresses,
                COUNT(DISTINCT city) as unique_cities,
                COUNT(DISTINCT zip_code) as unique_zip_codes,
                COUNT(DISTINCT created_by) as unique_creators
            FROM addresses
        """)
        stats = cursor.fetchone()
        cursor.close()
        return stats
    except Exception as e:
        logger.error(f"Error fetching address stats: {str(e)}")
        return {
            'total_addresses': 0,
            'unique_cities': 0,
            'unique_zip_codes': 0,
            'unique_creators': 0
        }

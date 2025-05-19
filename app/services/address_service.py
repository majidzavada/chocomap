from typing import Optional, List, Dict, Any
from app import mysql
from app.utils import sanitize_input
import logging
import requests
from requests.exceptions import RequestException
import os

logger = logging.getLogger(__name__)

class AddressService:
    @staticmethod
    def geocode_address(street: str, city: str, zip_code: str) -> Optional[Dict[str, float]]:
        """Geocode address using Google Maps API"""
        try:
            address = f"{street}, {city}, {zip_code}"
            params = {
                'address': address,
                'key': os.getenv('GOOGLE_MAPS_API_KEY')
            }
            
            response = requests.get(
                "https://maps.googleapis.com/maps/api/geocode/json",
                params=params,
                timeout=5
            )
            response.raise_for_status()
            data = response.json()
            
            if data['status'] == 'OK':
                location = data['results'][0]['geometry']['location']
                return {
                    'latitude': location['lat'],
                    'longitude': location['lng']
                }
            return None
        except (RequestException, KeyError, IndexError) as e:
            logger.error(f"Error geocoding address: {str(e)}")
            return None

    @staticmethod
    def create_address(
        label: str,
        street: str,
        city: str,
        zip_code: str,
        user_id: int,
        lat: Optional[float] = None,
        lon: Optional[float] = None
    ) -> Optional[int]:
        """Create a new address with geocoding"""
        cursor = mysql.connection.cursor()
        try:
            # Sanitize input
            label = sanitize_input(label)
            street = sanitize_input(street)
            city = sanitize_input(city)
            zip_code = sanitize_input(zip_code)
            
            # Geocode if coordinates not provided
            if lat is None or lon is None:
                coords = AddressService.geocode_address(street, city, zip_code)
                if coords:
                    lat = coords['latitude']
                    lon = coords['longitude']
                else:
                    logger.warning(f"Could not geocode address: {street}, {city}, {zip_code}")
                    return None
            
            cursor.execute("""
                INSERT INTO addresses (
                    label, street_address, city, zip_code,
                    latitude, longitude, created_by, created_at, updated_at
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW())
            """, (label, street, city, zip_code, lat, lon, user_id))
            
            mysql.connection.commit()
            return cursor.lastrowid
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error creating address: {str(e)}")
            return None
        finally:
            cursor.close()

    @staticmethod
    def update_address(
        address_id: int,
        label: Optional[str] = None,
        street: Optional[str] = None,
        city: Optional[str] = None,
        zip_code: Optional[str] = None
    ) -> bool:
        """Update address information"""
        cursor = mysql.connection.cursor()
        try:
            updates = []
            params = []
            
            if label is not None:
                updates.append("label = %s")
                params.append(sanitize_input(label))
            if street is not None:
                updates.append("street_address = %s")
                params.append(sanitize_input(street))
            if city is not None:
                updates.append("city = %s")
                params.append(sanitize_input(city))
            if zip_code is not None:
                updates.append("zip_code = %s")
                params.append(sanitize_input(zip_code))
            
            if not updates:
                return False
                
            # If address components changed, update coordinates
            if any([street, city, zip_code]):
                current = AddressService.get_address_by_id(address_id)
                if current:
                    coords = AddressService.geocode_address(
                        street or current['street_address'],
                        city or current['city'],
                        zip_code or current['zip_code']
                    )
                    if coords:
                        updates.append("latitude = %s")
                        params.append(coords['latitude'])
                        updates.append("longitude = %s")
                        params.append(coords['longitude'])
            
            updates.append("updated_at = NOW()")
            params.append(address_id)
            
            query = f"""
                UPDATE addresses 
                SET {', '.join(updates)}
                WHERE id = %s
            """
            
            cursor.execute(query, tuple(params))
            mysql.connection.commit()
            return cursor.rowcount > 0
        except Exception as e:
            mysql.connection.rollback()
            logger.error(f"Error updating address: {str(e)}")
            return False
        finally:
            cursor.close()

    @staticmethod
    def get_address_by_id(address_id: int) -> Optional[Dict[str, Any]]:
        """Get address by ID"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                SELECT * FROM addresses WHERE id = %s
            """, (address_id,))
            return cursor.fetchone()
        finally:
            cursor.close()

    @staticmethod
    def get_addresses_by_user(user_id: int) -> List[Dict[str, Any]]:
        """Get all addresses created by a user"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                SELECT * FROM addresses 
                WHERE created_by = %s
                ORDER BY created_at DESC
            """, (user_id,))
            return cursor.fetchall()
        finally:
            cursor.close()

    @staticmethod
    def get_address_stats() -> Dict[str, Any]:
        """Get address statistics"""
        cursor = mysql.connection.cursor()
        try:
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_addresses,
                    COUNT(DISTINCT city) as unique_cities,
                    COUNT(DISTINCT zip_code) as unique_zip_codes,
                    COUNT(DISTINCT created_by) as unique_users
                FROM addresses
            """)
            return cursor.fetchone()
        finally:
            cursor.close() 
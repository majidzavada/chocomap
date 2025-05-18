from app import mysql
import os
import requests

def get_deliveries_by_driver(driver_id, date=None):
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
    cursor.close()
    return result

def update_delivery_status(delivery_id, status):
    cursor = mysql.connection.cursor()
    cursor.execute("UPDATE deliveries SET status = %s WHERE id = %s", (status, delivery_id))
    mysql.connection.commit()
    cursor.close()

def get_all_deliveries_grouped(driver_filter=None, date_filter=None):
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
    cursor.close()

    grouped = {}
    for d in deliveries:
        key = (d['delivery_date'], d['driver_name'])
        if key not in grouped:
            grouped[key] = []
        grouped[key].append(d)
    return grouped

def create_delivery(driver_id, address_id, date, start_time, end_time, assigned_by, notes):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT latitude, longitude FROM addresses WHERE id = %s", (address_id,))
    address = cursor.fetchone()

    if not address:
        return

    dest_lat = address['latitude']
    dest_lng = address['longitude']
    wh_lat = os.getenv('WAREHOUSE_LAT')
    wh_lng = os.getenv('WAREHOUSE_LNG')

    params = {
        'origins': f"{wh_lat},{wh_lng}",
        'destinations': f"{dest_lat},{dest_lng}",
        'key': os.getenv("GOOGLE_MAPS_API_KEY")
    }

    response = requests.get("https://maps.googleapis.com/maps/api/distancematrix/json", params=params)
    data = response.json()

    try:
        eta = data['rows'][0]['elements'][0]['duration']['value'] // 60
    except:
        eta = None

    cursor.execute("""
        INSERT INTO deliveries (
            driver_id, address_id, delivery_date, start_time, end_time,
            assigned_by, notes, status, eta_minutes, return_eta_minutes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending', %s, %s)
    """, (driver_id, address_id, date, start_time, end_time,
          assigned_by, notes, eta, eta))

    mysql.connection.commit()
    cursor.close()

def delete_delivery(delivery_id):
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM deliveries WHERE id = %s", (delivery_id,))
    mysql.connection.commit()
    cursor.close()

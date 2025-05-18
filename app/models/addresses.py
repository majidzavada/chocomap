from app import mysql

def get_all_addresses():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM addresses ORDER BY label")
    addresses = cursor.fetchall()
    cursor.close()
    return addresses

def create_address(label, street, city, zip_code, lat, lon, user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("""
        INSERT INTO addresses (label, street_address, city, zip_code, latitude, longitude, created_by)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    """, (label, street, city, zip_code, lat, lon, user_id))
    mysql.connection.commit()
    cursor.close()

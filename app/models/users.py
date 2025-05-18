from app import mysql

def get_user_by_email(email):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE email = %s", (email,))
    user = cursor.fetchone()
    cursor.close()
    return user

def get_user_by_id(user_id):
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    cursor.close()
    return user

def get_all_drivers():
    cursor = mysql.connection.cursor()
    cursor.execute("SELECT id, name FROM users WHERE role = 'driver'")
    drivers = cursor.fetchall()
    cursor.close()
    return drivers

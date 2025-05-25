# 🍫 ChocoMap

ChocoMap is a warehouse delivery planning app for a chocolate company. It helps warehouse employees coordinate with drivers efficiently — including route planning, delivery tracking, and task management.

## 📦 Features

- **Authentication & Authorization**
  - Secure user authentication (login with email or username)
  - Role-based access control (Admin, Manager, Employee, Driver)
  - Password reset and change functionality
  - User registration approval system
  - Admin dashboard for user management

- **Driver Features**
  - Real-time delivery tracking
  - Route optimization with Google Maps
  - Delivery status updates
  - ETA calculations
  - Delivery history

- **Employee Features**
  - Delivery scheduling
  - Address management
  - Calendar view with filtering
  - Delivery statistics
  - Task assignment

- **Admin Features**
  - User approval system
  - User management (create, edit, delete)
  - Role management
  - System configuration
  - Access control

- **Manager Features**
  - Driver management
  - Performance analytics
  - Route optimization
  - Delivery reports
  - System configuration

- **General Features**
  - Multi-language support (English and Czech)
  - Language switching with persistence
  - Responsive design
  - Real-time updates
  - Data validation
  - Error handling

- **Delivery Scheduling**
  - Schedule deliveries with driver selection and destination search.
  - Integrated Google Maps for route planning and visualization.
  - Real-time route updates and distance calculations.

- **Google Maps Integration**
  - Autocomplete for destination search.
  - Route visualization with Directions API.
  - Support for advanced map features like distance and geometry calculations.

## 🚀 Tech Stack

- **Backend**
  - Python 3.8+
  - Flask 2.0+
  - SQLAlchemy ORM
  - MariaDB
  - Redis for caching and rate limiting
  - Gunicorn for deployment

- **Frontend**
  - Bootstrap 5
  - JavaScript (ES6+)
  - Google Maps API
  - FullCalendar.js
  - Chart.js

- **Internationalization**
  - Flask-Babel
  - Translation files (EN, CS)
  - Persistent language preferences

- **Testing**
  - pytest
  - Coverage reporting

## ⚙️ Setup

### Prerequisites
- Python 3.8 or higher
- MariaDB
- Redis (required for rate limiting and caching)
- Google Maps API key
- Build tools & MySQL/MariaDB client dev headers (e.g. `build-essential`, `python3-dev`, `default-libmysqlclient-dev` on Ubuntu/Debian) — required to compile the `mysqlclient` library

### System Requirements

1. **System packages (only once, required for mysqlclient)**
   ```bash
   sudo apt-get update
   sudo apt-get install build-essential python3-dev default-libmysqlclient-dev
   ```

2. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **MariaDB**
   ```bash
   sudo apt-get update
   sudo apt-get install mariadb-server
   ```

3. **Redis**
   ```bash
   sudo apt-get update
   sudo apt-get install redis-server
   sudo systemctl start redis-server
   sudo systemctl enable redis-server
   ```

4. **Verify Redis Installation**
   ```bash
   redis-cli ping
   # Should return PONG
   ```

### Development Installation

1. Clone the repository
```bash
git clone https://github.com/majidzavada/chocomap
cd chocomap
```

2. Create and activate virtual environment
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies
```bash
pip install -r requirements.txt
```

4. Set up environment variables
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. Initialize the database
```bash
flask db upgrade
```

6. Run the development server
```bash
flask run
```

### Production Deployment

1. Clone and setup as above (steps 1-5)

2. Create database and user
```sql
CREATE DATABASE chocomap;
CREATE USER 'choco'@'localhost' IDENTIFIED BY 'your_password';
GRANT ALL PRIVILEGES ON chocomap.* TO 'choco'@'localhost';
FLUSH PRIVILEGES;
```

3. Initialize database schema
```bash
mysql -u choco -p chocomap < migrations/create_users_table.sql
```

4. Run with Gunicorn
```bash
# Stop any existing Gunicorn processes
sudo pkill gunicorn
sudo rm -f gunicorn.pid

# Start Gunicorn
gunicorn --bind 0.0.0.0:8000 wsgi:app --pid gunicorn.pid --daemon
```

5. Default admin credentials
```
Username: Admin
Email: majid@steinerkovarik.com
Password: Admin123!
```

### Development

- Run tests: `pytest`
- Generate translations: `pybabel compile -d app/translations`
- Check code style: `flake8`
- Update translations: `pybabel update -i messages.pot -d app/translations`

## 📝 API Documentation

The API documentation is available at `/api/docs` when running the application.

## 🔒 Security

- CSRF protection
- Rate limiting (using Redis)
- Password hashing using bcrypt
- Input validation
- SQL injection prevention
- XSS protection
- User registration approval system
- Role-based access control

### Password Security

The application uses bcrypt for password hashing, which provides:
- Secure password storage with salt
- Protection against rainbow table attacks
- Configurable work factor for future-proofing
- Industry-standard password hashing algorithm

Password requirements:
- Minimum 8 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character

## 🌐 Internationalization

The application supports multiple languages:
- English (default)
- Czech

Language preferences are:
1. Stored in user profile if logged in
2. Stored in session if not logged in
3. Detected from browser settings as fallback

## 🤝 Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- Majid - Initial work

##  Acknowledgments

- Google Maps API
- Bootstrap team
- Flask community

---

## 🚀 Stack

- Python (Flask)
- MariaDB (via `flask_mysqldb`)
- Google Maps API
- Babel for i18n

---

## ⚙️ Setup

### 1. Clone the project
```bash
git clone https://github.com/majidzavada/chocomap
cd chocomap

```

### Database Schema Changes
- The `users` table now includes a `username` column (unique). You can log in with either your username or email address.

### Login
- You can now log in using either your email or your username.

### Default admin credentials
```
Username: Admin
Email: majid@steinerkovarik.com
Password: Admin123!
```

## Additional Dependencies

- `pymysql`: Used for database operations with dictionary-like cursors.

## System Settings

The System Settings section allows administrators to manage:
- Application settings (e.g., enabling/disabling logging and debugging).
- Email server settings (SMTP configuration).
- API keys for external services like Google Maps.

### Configuration Files
- `config/app_settings.json`: Stores application settings.
- `config/email_settings.json`: Stores email server settings.
- `config/api_keys.json`: Stores API keys for external services.

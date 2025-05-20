# 🍫 ChocoMap

ChocoMap is a warehouse delivery planning app for a chocolate company. It helps warehouse employees coordinate with drivers efficiently — including route planning, delivery tracking, and task management.

## 📦 Features

- **Authentication & Authorization**
  - Secure user authentication
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

### System Requirements

1. **Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **MariaDB**
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
Email: admin@chocomap.com
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
- Password hashing
- Input validation
- SQL injection prevention
- XSS protection
- User registration approval system
- Role-based access control

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

## �� Acknowledgments

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

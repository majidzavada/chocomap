# 🍫 ChocoMap

ChocoMap is a warehouse delivery planning app for a chocolate company. It helps warehouse employees coordinate with drivers efficiently — including route planning, delivery tracking, and task management.

## 📦 Features

- **Authentication & Authorization**
  - Secure user authentication
  - Role-based access control (Manager, Employee, Driver)
  - Password reset and change functionality

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

- **Manager Features**
  - Driver management
  - Performance analytics
  - Route optimization
  - Delivery reports
  - System configuration

- **General Features**
  - Multi-language support (English and Czech)
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
  - Redis for caching

- **Frontend**
  - Bootstrap 5
  - JavaScript (ES6+)
  - Google Maps API
  - FullCalendar.js
  - Chart.js

- **Internationalization**
  - Flask-Babel
  - Translation files (EN, CS)

- **Testing**
  - pytest
  - Coverage reporting

## ⚙️ Setup

### Prerequisites
- Python 3.8 or higher
- MariaDB
- Redis (optional, for caching)
- Google Maps API key

### Installation

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

6. Run the application
```bash
flask run
```

### Development

- Run tests: `pytest`
- Generate translations: `flask babel compile`
- Check code style: `flake8`

## 📝 API Documentation

The API documentation is available at `/api/docs` when running the application.

## 🔒 Security

- CSRF protection
- Rate limiting
- Password hashing
- Input validation
- SQL injection prevention
- XSS protection

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

## 🙏 Acknowledgments

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

# Evently - Event Booking System

Evently is a comprehensive Django-based event booking system that allows users to browse events, make bookings, and provides administrative tools for event management. The system features asynchronous processing with Celery, Redis caching, and a robust API architecture.

## 🏗️ Architecture Overview

### Technology Stack
- **Backend**: Django 5.2.6 with Django REST Framework
- **Database**: PostgreSQL (production) / SQLite (development)
- **Caching**: Redis
- **Task Queue**: Celery with Redis broker
- **Authentication**: Token-based authentication
- **Containerization**: Docker & Docker Compose

### System Components

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Django Web    │    │   Redis Cache   │    │  PostgreSQL DB  │
│     Server      │◄──►│   & Message     │◄──►│                 │
│                 │    │     Broker      │    │                 │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │
         ▼                       ▼
┌─────────────────┐    ┌─────────────────┐
│   Celery        │    │   Email         │
│   Workers       │    │   Service       │
└─────────────────┘    └─────────────────┘
```

### Application Structure

```
Evently/
├── admin_app/          # Event management and admin functionality
├── booking/           # Booking system with async processing
├── user/              # User authentication and profile management
├── utils/             # Utility functions and caching
├── templates/         # Email templates
└── Evently/           # Main Django project configuration
```

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Docker & Docker Compose
- Redis server
- PostgreSQL (optional, SQLite for development)

### Environment Setup

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd Evently
   ```

2. **Create environment file**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Run with Docker Compose**
   ```bash
   docker-compose up --build
   ```

4. **Or run locally**
   ```bash
   # Create virtual environment
   python -m venv myenv
   source myenv/bin/activate  # On Windows: myenv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Run migrations
   python manage.py migrate

   # Start Celery worker
   celery -A Evently worker --loglevel=info

   # Start Django server
   python manage.py runserver
   ```

## 📚 API Documentation

### Base URL
```
http://localhost:8000/api/
```

### Authentication
The API uses token-based authentication. Include the token in the Authorization header:
```
Authorization: Token <your-token>
```

---

## 🔐 User Authentication Endpoints

### Register User
**POST** `/api/user/auth/register/`

Creates a new user account.

**Request Body:**
```json
{
    "username": "john_doe",
    "email": "john@example.com",
    "password": "secure_password",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "address": "123 Main St, City"
}
```

**Response:**
```json
{
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "token": "abc123def456..."
}
```

### Login User
**POST** `/api/user/auth/login/`

Authenticates user and returns token.

**Request Body:**
```json
{
    "username": "john_doe",
    "password": "secure_password"
}
```

**Response:**
```json
{
    "token": "abc123def456..."
}
```

### Logout User
**POST** `/api/user/auth/logout/`

Invalidates the current user's token.

**Headers:** `Authorization: Token <token>`

**Response:**
```json
{
    "status": "logged_out"
}
```

### Get User Profile
**GET** `/api/user/auth/me/`

Returns current user's profile information.

**Headers:** `Authorization: Token <token>`

**Response:**
```json
{
    "id": 1,
    "username": "john_doe",
    "email": "john@example.com",
    "first_name": "John",
    "last_name": "Doe",
    "phone_number": "+1234567890",
    "address": "123 Main St, City",
    "is_staff": false,
    "is_superuser": false
}
```

---

## 🎫 Event Management Endpoints (Admin)

### Create Event
**POST** `/api/admin/events/`

Creates a new event (Admin/Staff only).

**Headers:** `Authorization: Token <admin-token>`

**Request Body:**
```json
{
    "name": "Tech Conference 2024",
    "venue": "Convention Center",
    "time": "2024-06-15T09:00:00Z",
    "capacity": 500,
    "description": "Annual technology conference",
    "price_per_ticket": 150.00
}
```

**Response:**
```json
{
    "event_id": "uuid-here",
    "name": "Tech Conference 2024",
    "venue": "Convention Center",
    "time": "2024-06-15T09:00:00Z",
    "capacity": 500
}
```

### List Events (Admin)
**GET** `/api/admin/events/list/`

Retrieves all events with admin-specific details.

**Headers:** `Authorization: Token <admin-token>`

**Query Parameters:**
- `status`: `upcoming` | `past`
- `venue`: Filter by venue name
- `is_active`: `true` | `false`
- `search`: Search in name/venue
- `ordering`: Sort by `time`, `created_at`, `capacity`

**Response:**
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/admin/events/list/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid-here",
            "name": "Tech Conference 2024",
            "venue": "Convention Center",
            "time": "2024-06-15T09:00:00Z",
            "capacity": 500,
            "available_tickets": 450,
            "price_per_ticket": 150.00,
            "organizer": "admin_user",
            "is_active": true,
            "created_at": "2024-01-01T10:00:00Z"
        }
    ]
}
```

### Get Event Details (Admin)
**GET** `/api/admin/events/{event_id}/details/`

Retrieves detailed information about a specific event.

**Headers:** `Authorization: Token <admin-token>`

**Response:**
```json
{
    "id": "uuid-here",
    "name": "Tech Conference 2024",
    "venue": "Convention Center",
    "time": "2024-06-15T09:00:00Z",
    "capacity": 500,
    "description": "Annual technology conference",
    "price_per_ticket": 150.00,
    "organizer": {
        "id": 1,
        "username": "admin_user",
        "email": "admin@example.com"
    },
    "is_active": true,
    "available_tickets": 450,
    "total_bookings": 50,
    "utilization_percentage": 10.0,
    "created_at": "2024-01-01T10:00:00Z",
    "updated_at": "2024-01-01T10:00:00Z"
}
```

### Update Event
**PUT** `/api/admin/events/{event_id}/`

Updates an existing event (Admin or Event Organizer only).

**Headers:** `Authorization: Token <token>`

**Request Body:**
```json
{
    "name": "Updated Tech Conference 2024",
    "capacity": 600,
    "price_per_ticket": 175.00
}
```

### Delete Event
**DELETE** `/api/admin/events/{event_id}/delete/`

Deletes an event (Admin or Event Organizer only).

**Headers:** `Authorization: Token <token>`

**Response:**
```json
{
    "event_id": "uuid-here",
    "status": "deleted"
}
```

### Notify Users
**POST** `/api/admin/events/{event_id}/notify/`

Sends notifications to all users who booked the event.

**Headers:** `Authorization: Token <admin-token>`

**Request Body:**
```json
{
    "message": "Event details have been updated. Please check the new information."
}
```

**Response:**
```json
{
    "status": "success",
    "message": "Notification sent to 150 users",
    "event_id": "uuid-here",
    "users_notified": 150
}
```

---

## 📊 Analytics Endpoints (Admin)

### General Analytics
**GET** `/api/admin/analytics/`

Retrieves overall booking analytics.

**Headers:** `Authorization: Token <admin-token>`

**Response:**
```json
{
    "total_bookings": 1250,
    "most_popular_events": [
        {
            "event_id": "uuid-here",
            "name": "Tech Conference 2024",
            "bookings": 450
        }
    ],
    "capacity_utilization": [
        {
            "event_id": "uuid-here",
            "name": "Tech Conference 2024",
            "utilization_percentage": 90.0
        }
    ]
}
```

### Event-Specific Analytics
**GET** `/api/admin/analytics/{event_id}/`

Retrieves detailed analytics for a specific event.

**Headers:** `Authorization: Token <admin-token>`

**Response:**
```json
{
    "event_id": "uuid-here",
    "total_bookings": 450,
    "cancellation_rate": 5.2,
    "daily_bookings": [
        {
            "date": "2024-01-01",
            "bookings": 15
        },
        {
            "date": "2024-01-02",
            "bookings": 23
        }
    ]
}
```

---

## 👥 User Management Endpoints (Admin)

### Create Staff User
**POST** `/api/admin/users/staff/`

Creates a new staff user (Superuser only).

**Headers:** `Authorization: Token <superuser-token>`

**Request Body:**
```json
{
    "username": "staff_user",
    "email": "staff@example.com",
    "password": "secure_password",
    "first_name": "Staff",
    "last_name": "User"
}
```

### Bulk Delete Test Users
**POST** `/api/admin/users/bulk_delete/`

Bulk deletes test users by username prefix.

**Headers:** `Authorization: Token <admin-token>`

**Request Body:**
```json
{
    "prefix": "test_"
}
```

**Response:**
```json
{
    "deleted_users": 25,
    "prefix": "test_"
}
```

---

## 🎟️ Public Event Endpoints

### Browse Events
**GET** `/api/user/events/`

Retrieves publicly available events with filtering options.

**Query Parameters:**
- `search`: Search in name, venue, description
- `date_from`: Filter events from date (YYYY-MM-DD)
- `date_to`: Filter events until date (YYYY-MM-DD)
- `venue`: Filter by venue name
- `min_price`: Minimum ticket price
- `max_price`: Maximum ticket price
- `available_only`: `true` to show only events with available tickets
- `upcoming_only`: `true` to show only upcoming events (default)
- `ordering`: Sort by `time`, `created_at`, `price_per_ticket`

**Response:**
```json
{
    "count": 15,
    "next": "http://localhost:8000/api/user/events/?page=2",
    "previous": null,
    "results": [
        {
            "id": "uuid-here",
            "name": "Tech Conference 2024",
            "venue": "Convention Center",
            "time": "2024-06-15T09:00:00Z",
            "capacity": 500,
            "available_tickets": 450,
            "price_per_ticket": 150.00,
            "description": "Annual technology conference",
            "organizer": "admin_user"
        }
    ]
}
```

### Get Event Details (Public)
**GET** `/api/user/events/{event_id}/`

Retrieves public event details.

**Response:**
```json
{
    "id": "uuid-here",
    "name": "Tech Conference 2024",
    "venue": "Convention Center",
    "time": "2024-06-15T09:00:00Z",
    "capacity": 500,
    "available_tickets": 450,
    "price_per_ticket": 150.00,
    "description": "Annual technology conference",
    "organizer": "admin_user"
}
```

---

## 🎫 Booking Endpoints

### Create Booking
**POST** `/api/bookings/`

Creates a new booking with asynchronous processing.

**Headers:** `Authorization: Token <user-token>`

**Request Body:**
```json
{
    "user_id": 1,
    "event_id": "uuid-here",
    "number_of_tickets": 2
}
```

**Response:**
```json
{
    "id": "booking-uuid",
    "event": {
        "id": "event-uuid",
        "name": "Tech Conference 2024"
    },
    "user": {
        "id": 1,
        "username": "john_doe"
    },
    "ticket_count": 2,
    "total_amount": 300.00,
    "booking_date": "2024-01-15T10:30:00Z",
    "status": "processing",
    "task_id": "celery-task-id"
}
```

### Cancel Booking
**DELETE** `/api/bookings/{booking_id}/`

Cancels an existing booking.

**Headers:** `Authorization: Token <user-token>`

**Response:**
```json
{
    "booking_id": "booking-uuid",
    "status": "cancelled"
}
```

### Get User Bookings
**GET** `/api/users/{user_id}/bookings/`

Retrieves booking history for a user.

**Headers:** `Authorization: Token <user-token>`

**Query Parameters:**
- `page`: Page number
- `page_size`: Items per page (max 100)

**Response:**
```json
{
    "count": 25,
    "next": "http://localhost:8000/api/users/1/bookings/?page=2",
    "previous": null,
    "results": [
        {
            "id": "booking-uuid",
            "event": {
                "id": "event-uuid",
                "name": "Tech Conference 2024",
                "venue": "Convention Center",
                "time": "2024-06-15T09:00:00Z"
            },
            "ticket_count": 2,
            "total_amount": 300.00,
            "booking_date": "2024-01-15T10:30:00Z",
            "status": "confirmed"
        }
    ]
}
```

### Check Event Availability
**GET** `/api/events/{event_id}/availability/`

Checks available tickets for an event.

**Response:**
```json
{
    "event_id": "event-uuid",
    "available_tickets": 450
}
```

---

## 🏥 System Endpoints

### Health Check
**GET** `/api/health/`

Checks system health and Celery worker status.

**Response:**
```json
{
    "status": "healthy",
    "celery": "running",
    "workers": 2,
    "broker": "redis://localhost:6379/0",
    "processes": ["celery worker processes"],
    "message": "Celery is running with 2 worker(s)"
}
```

---

## 🗄️ Data Models

### User Model
```python
class User(AbstractUser):
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Event Model
```python
class Event(models.Model):
    name = models.CharField(max_length=255)
    venue = models.CharField(max_length=255)
    time = models.DateTimeField()
    capacity = models.IntegerField()
    description = models.TextField(blank=True, null=True)
    price_per_ticket = models.DecimalField(max_digits=10, decimal_places=2)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
```

### Booking Model
```python
class Booking(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticket_count = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES)
    task_id = models.CharField(max_length=255, blank=True, null=True)
```

### Booking Status Options
- `pending`: Booking created, awaiting processing
- `processing`: Booking being processed asynchronously
- `confirmed`: Booking successfully confirmed
- `failed`: Booking processing failed
- `cancelled`: Booking cancelled by user or system

---

## ⚙️ Configuration

### Environment Variables
```bash
# Django Settings
DEBUG=False
SECRET_KEY=your-secret-key
ALLOWED_HOSTS=localhost,127.0.0.1

# Database
DB_NAME=evently_db
DB_USER=postgres
DB_PASSWORD=password
DB_HOST=localhost
DB_PORT=5432
DATABASE_URL=postgresql://user:pass@host:port/dbname

# Redis
REDIS_URL=redis://localhost:6379/0

# Email Configuration
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
DEFAULT_FROM_EMAIL=noreply@evently.com
```

### Celery Configuration
The system uses Celery for asynchronous task processing:
- **Broker**: Redis
- **Result Backend**: Redis
- **Task Serialization**: JSON
- **Worker Pool**: Solo (Windows compatibility)

### Caching
Redis is used for:
- API response caching
- Session storage
- Celery message broker

---

## 🔧 Development

### Running Tests
```bash
python manage.py test
```

### Database Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### Creating Superuser
```bash
python manage.py createsuperuser
```

### Celery Commands
```bash
# Start Celery worker
celery -A Evently worker --loglevel=info

# Start Celery beat (for periodic tasks)
celery -A Evently beat --loglevel=info

# Check Celery status
celery -A Evently inspect active
```

---

## 📝 API Features

### Pagination
All list endpoints support pagination:
- `page`: Page number
- `page_size`: Items per page (default: 10, max: 100)

### Filtering & Search
Most endpoints support filtering and search:
- **Search**: Text search in relevant fields
- **Ordering**: Sort by various fields
- **Date filtering**: Filter by date ranges
- **Price filtering**: Filter by price ranges

### Caching
API responses are cached using Redis:
- Event lists: 5 minutes
- Event details: 10 minutes
- User profiles: 15 minutes
- Analytics: 30 minutes

### Error Handling
Standardized error responses:
```json
{
    "error": "Error message",
    "details": "Additional error details"
}
```

---

## 🚀 Deployment

### Docker Deployment
```bash
docker-compose up --build -d
```

### Production Considerations
1. Set `DEBUG=False`
2. Use strong `SECRET_KEY`
3. Configure proper database
4. Set up Redis cluster
5. Configure email service
6. Set up monitoring
7. Enable HTTPS
8. Configure proper logging

---

## 📄 License

This project is licensed under the MIT License.

---

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

---

## 📞 Support

For support and questions, please contact the development team or create an issue in the repository.

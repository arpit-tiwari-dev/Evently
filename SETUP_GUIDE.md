# Evently Booking API - Setup Guide

## Quick Start

### Option 1: Docker Deployment (Recommended)

1. **Prerequisites:**
   - Docker and Docker Compose installed
   - Git (to clone the repository)

2. **Setup and Run:**
   ```bash
   # Navigate to the Evently directory
   cd Evently
   
   # Create environment file
   cp env.example .env
   
   # Build and run with Docker
   docker-compose up --build
   ```

3. **Create Superuser:**
   ```bash
   docker-compose exec web python manage.py createsuperuser
   ```

4. **Access the Application:**
   - API: http://localhost:8000/api/
   - Admin: http://localhost:8000/admin/

For detailed Docker deployment instructions, see [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md)

### Option 2: Local Development Setup

#### 1. Database Setup
```bash
# Navigate to the Evently directory
cd Evently

# Install dependencies
pip install -r requirements.txt

# Create and apply migrations
python manage.py makemigrations
python manage.py migrate

# Create a superuser for admin access
python manage.py createsuperuser
```

#### 2. Start the Development Server
```bash
python manage.py runserver
```

The API will be available at: `http://localhost:8000/api/`

### 3. Create Test Data

#### Option A: Using Django Admin (Recommended)
1. Go to `http://localhost:8000/admin/`
2. Login with your superuser credentials
3. Create test events in the "Events" section
4. Create test users in the "Users" section

#### Option B: Using Django Shell
```python
python manage.py shell

# Create a test event
from admin_app.models import Event
from datetime import date, time

event = Event.objects.create(
    name="Test Concert",
    available_tickets=100,
    organizer="Test Organizer",
    description="A test concert for API testing",
    date=date(2024, 12, 31),
    time=time(20, 0),
    location="Test Venue",
    price_per_ticket=25.00
)
print(f"Created event with ID: {event.id}")

# Create a test user
from django.contrib.auth import get_user_model
User = get_user_model()

user = User.objects.create_user(
    username="testuser",
    email="test@example.com",
    password="testpass123"
)
print(f"Created user with ID: {user.id}")
```

### 4. Get Authentication Token
```bash
# Create a token for API authentication
python manage.py shell

from rest_framework.authtoken.models import Token
from django.contrib.auth import get_user_model

User = get_user_model()
user = User.objects.get(username="testuser")
token, created = Token.objects.get_or_create(user=user)
print(f"Token: {token.key}")
```

## API Testing

### Using the Test Script
1. Update the `AUTH_TOKEN` in `test_api.py` with your token
2. Update `test_user_id` and `test_event_id` with actual IDs
3. Run the test:
```bash
python test_api.py
```

### Using cURL

#### Check Event Availability
```bash
curl -X GET http://localhost:8000/api/events/1/availability/
```

#### Book Tickets
```bash
curl -X POST http://localhost:8000/api/bookings/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token YOUR_TOKEN_HERE" \
  -d '{"user_id": "1", "event_id": "1", "number_of_tickets": 2}'
```

#### Get User Booking History
```bash
curl -X GET http://localhost:8000/api/users/1/bookings/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

#### Cancel Booking
```bash
curl -X DELETE http://localhost:8000/api/bookings/1/ \
  -H "Authorization: Token YOUR_TOKEN_HERE"
```

### Using Python Requests
```python
import requests

# Set up authentication
headers = {
    'Content-Type': 'application/json',
    'Authorization': 'Token YOUR_TOKEN_HERE'
}

# Check availability
response = requests.get('http://localhost:8000/api/events/1/availability/')
print(response.json())

# Book tickets
booking_data = {
    "user_id": "1",
    "event_id": "1", 
    "number_of_tickets": 2
}
response = requests.post(
    'http://localhost:8000/api/bookings/',
    json=booking_data,
    headers=headers
)
print(response.json())
```

## Production Deployment

### Environment Variables
Create a `.env` file or set environment variables:
```bash
DEBUG=False
SECRET_KEY=your-production-secret-key
DB_NAME=evently_db
DB_USER=postgres
DB_PASSWORD=your-secure-password
DB_HOST=localhost
DB_PORT=5432
```

### Database Migration
```bash
# For PostgreSQL (recommended for production)
pip install psycopg2-binary

# Run migrations
python manage.py migrate
```

### Docker Production Deployment
For production deployment with Docker, see the [DOCKER_DEPLOYMENT.md](DOCKER_DEPLOYMENT.md) guide for:
- SSL/HTTPS setup
- Database backup strategies
- Static file serving
- Monitoring and logging
- Scaling considerations

### Security Considerations
1. Set `DEBUG=False` in production
2. Use a strong `SECRET_KEY`
3. Configure proper `ALLOWED_HOSTS`
4. Use HTTPS in production
5. Set up proper logging and monitoring

## Troubleshooting

### Common Issues

#### 1. Import Errors
If you get import errors, make sure all apps are in `INSTALLED_APPS`:
```python
INSTALLED_APPS = [
    # ... other apps
    'rest_framework',
    'admin_app',
    'booking', 
    'user',
]
```

#### 2. Migration Issues
```bash
# Reset migrations if needed
python manage.py migrate --fake-initial
```

#### 3. Authentication Issues
- Make sure you're using the correct token format: `Token YOUR_TOKEN_HERE`
- Verify the user exists and has a token
- Check that the token hasn't expired

#### 4. Database Issues
- Ensure the database is properly migrated
- Check that test data exists
- Verify foreign key relationships

### Logging
Check the `booking.log` file for detailed error logs:
```bash
tail -f booking.log
```

## Performance Testing

### Load Testing with Apache Bench
```bash
# Test availability endpoint (no auth required)
ab -n 1000 -c 10 http://localhost:8000/api/events/1/availability/

# Test booking endpoint (requires auth)
ab -n 100 -c 5 -H "Authorization: Token YOUR_TOKEN" \
   -p booking_data.json -T "application/json" \
   http://localhost:8000/api/bookings/
```

### Concurrent Booking Test
```python
import threading
import requests

def book_tickets():
    headers = {'Authorization': 'Token YOUR_TOKEN'}
    data = {"user_id": "1", "event_id": "1", "number_of_tickets": 1}
    response = requests.post('http://localhost:8000/api/bookings/', 
                           json=data, headers=headers)
    print(f"Status: {response.status_code}, Response: {response.json()}")

# Run 10 concurrent booking attempts
threads = []
for i in range(10):
    t = threading.Thread(target=book_tickets)
    threads.append(t)
    t.start()

for t in threads:
    t.join()
```

## Monitoring

### Key Metrics to Monitor
1. **Booking Success Rate**: Percentage of successful bookings
2. **Capacity Utilization**: How quickly events sell out
3. **API Response Times**: Performance under load
4. **Error Rates**: Failed bookings and their causes
5. **Concurrent Users**: Peak usage patterns

### Log Analysis
```bash
# Count successful bookings
grep "Booking created successfully" booking.log | wc -l

# Count failed bookings
grep "Booking failed" booking.log | wc -l

# Check for capacity issues
grep "insufficient tickets" booking.log
```

## Support

For additional help:
1. Check the API documentation in `API_DOCUMENTATION.md`
2. Review Django REST Framework documentation
3. Check the Django logs for detailed error information
4. Test with the provided test script

## Next Steps

1. **Add Caching**: Implement Redis for better performance
2. **Add Rate Limiting**: Prevent abuse with throttling
3. **Add Webhooks**: Notify external systems of booking events
4. **Add Payment Integration**: Process payments with booking
5. **Add Email Notifications**: Send confirmation emails
6. **Add Mobile App**: Create mobile client using this API

# Evently Booking API Documentation

## Overview
This API provides comprehensive booking management functionality for events, including ticket booking, cancellation, history tracking, and availability checking.

## Base URL
```
http://localhost:8000/api/
```

## Authentication
All endpoints require authentication using Django REST Framework's authentication system. You can use either:
- Session Authentication (for web browsers)
- Token Authentication (for API clients)

## Endpoints

### 1. Book Ticket API

**Endpoint:** `POST /api/bookings/`

**Description:** Allows users to book tickets for an event with capacity checking and transaction safety.

**Request Body:**
```json
{
  "user_id": "string",
  "event_id": "string", 
  "number_of_tickets": "integer"
}
```

**Response (Success - 201 Created):**
```json
{
  "booking_id": "string",
  "event_id": "string",
  "user_id": "string",
  "number_of_tickets": "integer",
  "status": "confirmed",
  "timestamp": "2024-01-15T10:30:00Z",
  "total_amount": "50.00"
}
```

**Response (Error - 409 Conflict):**
```json
{
  "error": "Insufficient tickets",
  "available_tickets": 5,
  "requested_tickets": 10
}
```

**Features:**
- ✅ Capacity checking before booking
- ✅ Atomic transactions to prevent overselling
- ✅ Pessimistic locking for concurrent requests
- ✅ Automatic total amount calculation
- ✅ Comprehensive error handling

---

### 2. Cancel Booking API

**Endpoint:** `DELETE /api/bookings/{booking_id}/`

**Description:** Allows users to cancel a previously made booking with atomic capacity updates.

**Response (Success - 200 OK):**
```json
{
  "booking_id": "string",
  "status": "cancelled"
}
```

**Response (Error - 404 Not Found):**
```json
{
  "error": "Booking not found"
}
```

**Response (Error - 400 Bad Request):**
```json
{
  "error": "Booking is already cancelled"
}
```

**Features:**
- ✅ Booking existence validation
- ✅ Atomic capacity restoration
- ✅ Concurrent cancellation safety
- ✅ Status validation

---

### 3. Booking History API

**Endpoint:** `GET /api/users/{user_id}/bookings/`

**Description:** Retrieve paginated booking history for a specific user.

**Query Parameters:**
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 10, max: 100)

**Response (Success - 200 OK):**
```json
{
  "count": 25,
  "next": "http://localhost:8000/api/users/123/bookings/?page=3",
  "previous": "http://localhost:8000/api/users/123/bookings/?page=1",
  "results": [
    {
      "booking_id": "string",
      "event_id": "string",
      "number_of_tickets": "integer",
      "status": "confirmed",
      "timestamp": "2024-01-15T10:30:00Z"
    }
  ]
}
```

**Features:**
- ✅ Paginated results
- ✅ Chronological ordering (newest first)
- ✅ Comprehensive booking details
- ✅ User validation

---

### 4. Check Availability API

**Endpoint:** `GET /api/events/{event_id}/availability/`

**Description:** Get real-time ticket availability for an event.

**Response (Success - 200 OK):**
```json
{
  "event_id": "string",
  "available_tickets": "integer"
}
```

**Response (Error - 404 Not Found):**
```json
{
  "error": "Event not found"
}
```

**Features:**
- ✅ Real-time availability
- ✅ No authentication required
- ✅ Event validation
- ✅ Accurate capacity reporting

---

## Error Handling

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 201 | Created |
| 400 | Bad Request - Invalid data or business logic error |
| 401 | Unauthorized - Authentication required |
| 404 | Not Found - Resource doesn't exist |
| 409 | Conflict - Business rule violation (e.g., insufficient tickets) |
| 500 | Internal Server Error |

### Error Response Format
```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

---

## Security Features

### Authentication & Authorization
- All booking endpoints require authentication
- Users can only access their own booking history
- Token-based authentication for API clients
- Session authentication for web applications

### Data Protection
- Input validation on all endpoints
- SQL injection prevention through Django ORM
- XSS protection through DRF serializers

---

## Performance & Scalability

### Concurrency Handling
- **Pessimistic Locking**: Uses `select_for_update()` to prevent race conditions
- **Atomic Transactions**: All booking operations are wrapped in database transactions
- **Capacity Management**: Real-time capacity updates with F() expressions

### Database Optimization
- Proper indexing on `event_id`, `user_id`, and `booking_date`
- Efficient queries with `select_related()` for foreign keys
- Pagination to handle large datasets

### Caching Strategy
- Event availability can be cached with TTL
- Consider Redis for high-traffic scenarios
- Database query optimization

---

## Monitoring & Logging

### Logging
- All booking operations are logged
- Error tracking for failed bookings
- Performance metrics for capacity checks
- Audit trail for cancellations

### Metrics to Track
- Booking success/failure rates
- Peak usage times
- Capacity utilization
- API response times

---

## Testing Recommendations

### Unit Tests
- Test transaction rollback scenarios
- Test concurrent booking attempts
- Test capacity validation logic
- Test error handling paths

### Load Tests
- Simulate concurrent booking requests
- Test capacity exhaustion scenarios
- Verify transaction isolation
- Performance under high load

---

## Example Usage

### Python Client Example
```python
import requests

# Authentication
headers = {'Authorization': 'Token your-auth-token'}

# Check availability
response = requests.get('http://localhost:8000/api/events/123/availability/')
print(response.json())

# Book tickets
booking_data = {
    "user_id": "456",
    "event_id": "123",
    "number_of_tickets": 2
}
response = requests.post(
    'http://localhost:8000/api/bookings/', 
    json=booking_data, 
    headers=headers
)
print(response.json())

# Get booking history
response = requests.get(
    'http://localhost:8000/api/users/456/bookings/', 
    headers=headers
)
print(response.json())

# Cancel booking
response = requests.delete(
    'http://localhost:8000/api/bookings/789/', 
    headers=headers
)
print(response.json())
```

### cURL Examples
```bash
# Check availability
curl -X GET http://localhost:8000/api/events/123/availability/

# Book tickets
curl -X POST http://localhost:8000/api/bookings/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your-auth-token" \
  -d '{"user_id": "456", "event_id": "123", "number_of_tickets": 2}'

# Get booking history
curl -X GET http://localhost:8000/api/users/456/bookings/ \
  -H "Authorization: Token your-auth-token"

# Cancel booking
curl -X DELETE http://localhost:8000/api/bookings/789/ \
  -H "Authorization: Token your-auth-token"
```

---

## Deployment Considerations

### Environment Variables
- `DEBUG=False` for production
- `SECRET_KEY` should be properly secured
- Database connection settings
- Logging configuration

### Database Setup
```bash
python manage.py makemigrations
python manage.py migrate
python manage.py createsuperuser
```

### Production Recommendations
- Use PostgreSQL for better concurrency handling
- Implement Redis for caching
- Set up proper logging and monitoring
- Use HTTPS in production
- Implement rate limiting
- Set up database backups

---

## Support

For issues or questions regarding this API, please refer to the Django REST Framework documentation or contact the development team.

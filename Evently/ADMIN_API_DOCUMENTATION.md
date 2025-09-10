# Evently Admin API Documentation

This document provides comprehensive documentation for all admin APIs in the Evently system.

## Base URL
All admin APIs are prefixed with `/api/admin/`

## Authentication
All admin APIs require authentication. Use Django's authentication system with admin user credentials.

---

## 1. Create Event

**Endpoint:** `POST /api/admin/events/`

**Description:** Allows admin to create a new event.

**Request Body:**
```json
{
  "name": "string",
  "venue": "string", 
  "time": "datetime",
  "capacity": "integer",
  "description": "string (optional)",
  "price_per_ticket": "decimal (optional, default: 0.00)"
}
```

**Response:**
```json
{
  "event_id": "string",
  "name": "string",
  "venue": "string",
  "time": "datetime",
  "capacity": "integer"
}
```

**Requirements:**
- ✅ Validates event details (no past dates, capacity positive)
- ✅ Stores with correct initial availability
- ✅ Returns event ID and details

---

## 2. Update Event

**Endpoint:** `PUT /api/admin/events/{event_id}/`

**Description:** Allows admin to update event details.

**Request Body:**
```json
{
  "name": "string",
  "venue": "string",
  "time": "datetime", 
  "capacity": "integer",
  "description": "string (optional)",
  "price_per_ticket": "decimal (optional)"
}
```

**Response:**
```json
{
  "event_id": "string",
  "name": "string",
  "venue": "string",
  "time": "datetime",
  "capacity": "integer"
}
```

**Requirements:**
- ✅ Validates updates against existing bookings
- ✅ Ensures capacity cannot be reduced below current bookings
- ✅ Handles concurrent edits safely

---

## 3. Delete Event

**Endpoint:** `DELETE /api/admin/events/{event_id}/delete/`

**Description:** Allows admin to delete an event.

**Response:**
```json
{
  "event_id": "string",
  "status": "deleted"
}
```

**Requirements:**
- ✅ Checks if event has active bookings
- ✅ Blocks deletion if bookings exist
- ✅ Returns meaningful error if not allowed

---

## 4. List All Events

**Endpoint:** `GET /api/admin/events/list/`

**Description:** Retrieve all events with filtering and pagination.

**Query Parameters:**
- `status`: Filter by status (`upcoming`, `past`)
- `venue`: Filter by venue (partial match)
- `is_active`: Filter by active status (`true`, `false`)
- `search`: Search in name and venue fields
- `ordering`: Order by fields (`time`, `created_at`, `capacity`)
- `page`: Page number for pagination
- `page_size`: Number of items per page (max 100)

**Response:**
```json
{
  "count": "integer",
  "next": "string|null",
  "previous": "string|null", 
  "results": [
    {
      "id": "string",
      "name": "string",
      "venue": "string",
      "time": "datetime",
      "capacity": "integer",
      "available_tickets": "integer",
      "is_active": "boolean"
    }
  ]
}
```

**Requirements:**
- ✅ Supports filters (upcoming, past, by venue)
- ✅ Paginates for performance

---

## 5. View Event Details

**Endpoint:** `GET /api/admin/events/{event_id}/details/`

**Description:** Retrieve specific event details.

**Response:**
```json
{
  "id": "string",
  "name": "string",
  "venue": "string",
  "time": "datetime",
  "capacity": "integer",
  "available_tickets": "integer",
  "description": "string",
  "price_per_ticket": "decimal",
  "organizer": "string",
  "is_active": "boolean",
  "total_bookings": "integer",
  "utilization_percentage": "float",
  "created_at": "datetime",
  "updated_at": "datetime"
}
```

**Requirements:**
- ✅ Includes current bookings count
- ✅ Shows utilization percentage

---

## 6. View Booking Analytics

**Endpoint:** `GET /api/admin/analytics/`

**Description:** Provides aggregated data for insights.

**Response:**
```json
{
  "total_bookings": "integer",
  "most_popular_events": [
    {
      "event_id": "string",
      "name": "string", 
      "bookings": "integer"
    }
  ],
  "capacity_utilization": [
    {
      "event_id": "string",
      "name": "string",
      "utilization_percentage": "float"
    }
  ]
}
```

**Requirements:**
- ✅ Aggregates from bookings
- ✅ Handles large datasets efficiently

---

## 7. Advanced Analytics (Event-Specific)

**Endpoint:** `GET /api/admin/analytics/{event_id}/`

**Description:** Detailed stats for a specific event.

**Response:**
```json
{
  "event_id": "string",
  "total_bookings": "integer",
  "cancellation_rate": "float",
  "daily_bookings": [
    {
      "date": "yyyy-mm-dd",
      "bookings": "integer"
    }
  ]
}
```

**Requirements:**
- ✅ Provides historical insights
- ✅ Shows trends over last 30 days

---

## 8. Notify Users

**Endpoint:** `POST /api/admin/events/{event_id}/notify/`

**Description:** Send notifications to users about event changes or cancellations.

**Request Body:**
```json
{
  "message": "string"
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Notification sent to X users"
}
```

**Requirements:**
- ✅ Handles notifications in batches
- ✅ Avoids spamming users

---

# User APIs

## Base URL
All user APIs are prefixed with `/api/`

---

## 1. Browse Events

**Endpoint:** `GET /api/events/`

**Description:** List events with availability and filtering.

**Query Parameters:**
- `date_from`: Filter events from this date
- `date_to`: Filter events until this date
- `venue`: Filter by venue (partial match)
- `min_price`: Minimum price filter
- `max_price`: Maximum price filter
- `available_only`: Show only events with available tickets (`true`/`false`)
- `upcoming_only`: Show only upcoming events (`true`/`false`, default: `true`)
- `search`: Search in name, venue, description
- `ordering`: Order by fields (`time`, `created_at`, `price_per_ticket`)
- `page`: Page number for pagination
- `page_size`: Number of items per page (max 100)

**Response:**
```json
{
  "count": "integer",
  "next": "string|null",
  "previous": "string|null",
  "results": [
    {
      "event_id": "string",
      "name": "string",
      "venue": "string", 
      "time": "datetime",
      "capacity": "integer",
      "available_tickets": "integer",
      "price_per_ticket": "decimal",
      "description": "string"
    }
  ]
}
```

---

## 2. View Event Details

**Endpoint:** `GET /api/events/{event_id}/`

**Description:** Show complete event information and available tickets.

**Response:**
```json
{
  "event_id": "string",
  "name": "string",
  "venue": "string",
  "time": "datetime", 
  "capacity": "integer",
  "available_tickets": "integer",
  "description": "string",
  "price_per_ticket": "decimal",
  "total_bookings": "integer",
  "utilization_percentage": "float",
  "created_at": "datetime"
}
```

---

## 3. Check Availability

**Endpoint:** `GET /api/events/{event_id}/availability/`

**Description:** Check available tickets for an event.

**Response:**
```json
{
  "event_id": "string",
  "available_tickets": "integer"
}
```

---

## 4. Book Tickets

**Endpoint:** `POST /api/bookings/`

**Description:** Book tickets for an event.

**Request Body:**
```json
{
  "user_id": "string",
  "event_id": "string",
  "number_of_tickets": "integer"
}
```

**Response:**
```json
{
  "booking_id": "string",
  "event_id": "string",
  "user_id": "string",
  "number_of_tickets": "integer",
  "status": "confirmed",
  "timestamp": "datetime",
  "total_amount": "decimal"
}
```

---

## 5. Cancel Booking

**Endpoint:** `DELETE /api/bookings/{booking_id}/`

**Description:** Cancel a booking.

**Response:**
```json
{
  "booking_id": "string",
  "status": "cancelled"
}
```

---

## 6. Booking History

**Endpoint:** `GET /api/users/{user_id}/bookings/`

**Description:** Get booking history for a user.

**Response:**
```json
{
  "count": "integer",
  "next": "string|null",
  "previous": "string|null",
  "results": [
    {
      "booking_id": "string",
      "event_id": "string",
      "number_of_tickets": "integer",
      "status": "string",
      "timestamp": "datetime"
    }
  ]
}
```

---

## Error Responses

All APIs return appropriate HTTP status codes and error messages:

- `400 Bad Request`: Invalid input data
- `401 Unauthorized`: Authentication required
- `403 Forbidden`: Insufficient permissions
- `404 Not Found`: Resource not found
- `409 Conflict`: Business logic conflict (e.g., insufficient tickets)
- `500 Internal Server Error`: Server error

**Error Response Format:**
```json
{
  "error": "Error message",
  "details": "Additional error details (optional)"
}
```

---

## Key Features Implemented

### Data Integrity
- ✅ Cannot reduce capacity below booked seats
- ✅ Atomic transactions for booking operations
- ✅ Pessimistic locking to prevent race conditions

### Security
- ✅ Admin-only access for event management
- ✅ Proper authentication and authorization
- ✅ Input validation and sanitization

### Performance
- ✅ Pagination for large datasets
- ✅ Efficient database queries with proper indexing
- ✅ Caching-friendly design

### Scalability
- ✅ Handles thousands of events and bookings
- ✅ Real-time availability updates
- ✅ Optimized analytics queries

### User Experience
- ✅ Accurate availability information
- ✅ Comprehensive filtering and search
- ✅ Consistent data under load

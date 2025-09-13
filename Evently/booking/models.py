from django.db import models
from admin_app.models import Event
from django.contrib.auth import get_user_model
from Evently.enums import BOOKING_STATUS_CHOICES

User = get_user_model()

# Create your models here.

class Booking(models.Model):
    """
    Booking model representing a booking for an event
    """
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    ticket_count = models.IntegerField()
    total_amount = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=BOOKING_STATUS_CHOICES)
    task_id = models.CharField(max_length=255, blank=True, null=True, help_text="Celery task ID for async processing")

    class Meta:
        indexes = [
            # Most critical indexes for booking performance
            models.Index(fields=['status'], name='booking_status_idx'),
            models.Index(fields=['event', 'status'], name='booking_event_status_idx'),
            models.Index(fields=['user'], name='booking_user_idx'),
            models.Index(fields=['user', 'booking_date'], name='booking_user_date_idx'),
            models.Index(fields=['booking_date'], name='booking_date_idx'),
            models.Index(fields=['task_id'], name='booking_task_idx'),
            # Composite indexes for common query patterns
            models.Index(fields=['event', 'user', 'status'], name='booking_event_user_status_idx'),
            models.Index(fields=['status', 'booking_date'], name='booking_status_date_idx'),
            # Index for availability calculations
            models.Index(fields=['event', 'status'], name='booking_availability_idx'),
        ]
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.contrib.auth import get_user_model

User = get_user_model()

# Create your models here.
class Event(models.Model):
    """
    Event model representing an event that can be booked
    """
    name = models.CharField(max_length=255)
    venue = models.CharField(max_length=255)
    time = models.DateTimeField()  # Combined date and time
    capacity = models.IntegerField()  # Total capacity
    description = models.TextField(blank=True, null=True)
    price_per_ticket = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - {self.venue}"

    def clean(self):
        """Validate event data"""
        if self.capacity <= 0:
            raise ValidationError("Capacity must be a positive integer")
        
        if self.time <= timezone.now():
            raise ValidationError("Event time must be in the future")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    @property
    def available_tickets(self):
        """Calculate available tickets based on confirmed bookings"""
        from booking.models import Booking
        confirmed_bookings = Booking.objects.filter(
            event=self, 
            status='confirmed'
        ).aggregate(total=models.Sum('ticket_count'))['total'] or 0
        return max(0, self.capacity - confirmed_bookings)

    @property
    def total_bookings(self):
        """Get total number of confirmed bookings"""
        from booking.models import Booking
        return Booking.objects.filter(event=self, status='confirmed').count()

    @property
    def utilization_percentage(self):
        """Calculate capacity utilization percentage"""
        if self.capacity == 0:
            return 0
        return round((self.capacity - self.available_tickets) / self.capacity * 100, 2)
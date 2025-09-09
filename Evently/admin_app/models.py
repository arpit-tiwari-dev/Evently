from django.db import models

# Create your models here.
class Event(models.Model):
    name = models.CharField(max_length=255)
    available_tickets = models.IntegerField()
    organizer = models.CharField(max_length=255)
    open_for_booking = models.BooleanField(default=True)
    description = models.TextField()
    date = models.DateField()
    time = models.TimeField()
    location = models.CharField(max_length=255)
    price_per_ticket = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
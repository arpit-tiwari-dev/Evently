from rest_framework import serializers
from django.utils import timezone
from django.db import models
from .models import Event
from booking.models import Booking


class EventCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating events"""
    
    class Meta:
        model = Event
        fields = ['name', 'venue', 'time', 'capacity', 'description', 'price_per_ticket']
    
    def validate_capacity(self, value):
        """Validate capacity is positive"""
        if value <= 0:
            raise serializers.ValidationError("Capacity must be a positive integer")
        return value
    
    def validate_time(self, value):
        """Validate event time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Event time must be in the future")
        return value


class EventUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating events"""
    
    class Meta:
        model = Event
        fields = ['name', 'venue', 'time', 'capacity', 'description', 'price_per_ticket']
    
    def validate_capacity(self, value):
        """Validate capacity is positive and not below current bookings"""
        if value <= 0:
            raise serializers.ValidationError("Capacity must be a positive integer")
        
        # Check if capacity is being reduced below current bookings
        if self.instance:
            current_bookings = Booking.objects.filter(
                event=self.instance, 
                status='confirmed'
            ).aggregate(total=models.Sum('ticket_count'))['total'] or 0
            
            if value < current_bookings:
                raise serializers.ValidationError(
                    f"Cannot reduce capacity below current bookings ({current_bookings})"
                )
        
        return value
    
    def validate_time(self, value):
        """Validate event time is in the future"""
        if value <= timezone.now():
            raise serializers.ValidationError("Event time must be in the future")
        return value


class EventListSerializer(serializers.ModelSerializer):
    """Serializer for listing events with availability info"""
    available_tickets = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = ['id', 'name', 'venue', 'time', 'capacity', 'available_tickets', 'is_active']


class EventDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed event view"""
    available_tickets = serializers.ReadOnlyField()
    total_bookings = serializers.ReadOnlyField()
    utilization_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = [
            'id', 'name', 'venue', 'time', 'capacity', 'available_tickets',
            'description', 'price_per_ticket', 'organizer', 'is_active',
            'total_bookings', 'utilization_percentage', 'created_at', 'updated_at'
        ]


class EventDeleteSerializer(serializers.Serializer):
    """Serializer for event deletion response"""
    event_id = serializers.CharField()
    status = serializers.CharField()


class AnalyticsSerializer(serializers.Serializer):
    """Serializer for analytics data"""
    total_bookings = serializers.IntegerField()
    most_popular_events = serializers.ListField()
    capacity_utilization = serializers.ListField()


class EventAnalyticsSerializer(serializers.Serializer):
    """Serializer for individual event analytics"""
    event_id = serializers.CharField()
    total_bookings = serializers.IntegerField()
    cancellation_rate = serializers.FloatField()
    daily_bookings = serializers.ListField()


class NotificationSerializer(serializers.Serializer):
    """Serializer for sending notifications"""
    message = serializers.CharField(max_length=1000)
    subject = serializers.CharField(max_length=200, required=False, help_text="Optional custom subject for the notification email")

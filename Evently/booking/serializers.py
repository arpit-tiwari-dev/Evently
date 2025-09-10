from rest_framework import serializers
from .models import Booking
from admin_app.models import Event
from django.contrib.auth import get_user_model

User = get_user_model()


class BookingSerializer(serializers.ModelSerializer):
    """
    Serializer for Booking model
    """
    booking_id = serializers.CharField(source='id', read_only=True)
    event_id = serializers.CharField(source='event.id', read_only=True)
    user_id = serializers.CharField(source='user.id', read_only=True)
    number_of_tickets = serializers.IntegerField(source='ticket_count')
    timestamp = serializers.DateTimeField(source='booking_date', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'booking_id', 'event_id', 'user_id', 'number_of_tickets', 
            'status', 'timestamp', 'total_amount'
        ]
        read_only_fields = ['booking_id', 'event_id', 'user_id', 'timestamp', 'total_amount']


class CreateBookingSerializer(serializers.Serializer):
    """
    Serializer for creating a new booking
    """
    user_id = serializers.CharField()
    event_id = serializers.CharField()
    number_of_tickets = serializers.IntegerField(min_value=1)
    
    def validate_user_id(self, value):
        """Validate that user exists"""
        try:
            User.objects.get(id=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User not found")
        return value
    
    def validate_event_id(self, value):
        """Validate that event exists"""
        try:
            event = Event.objects.get(id=value)
            if not event.is_active:
                raise serializers.ValidationError("Event is not active")
        except Event.DoesNotExist:
            raise serializers.ValidationError("Event not found")
        return value
    
    def validate(self, data):
        """Validate booking capacity"""
        event_id = data.get('event_id')
        number_of_tickets = data.get('number_of_tickets')
        
        if event_id and number_of_tickets:
            try:
                event = Event.objects.get(id=event_id)
                if event.available_tickets < number_of_tickets:
                    raise serializers.ValidationError(
                        f"Not enough tickets available. Available: {event.available_tickets}, Requested: {number_of_tickets}"
                    )
            except Event.DoesNotExist:
                raise serializers.ValidationError("Event not found")
        
        return data


class BookingHistorySerializer(serializers.ModelSerializer):
    """
    Serializer for booking history
    """
    booking_id = serializers.CharField(source='id', read_only=True)
    event_id = serializers.CharField(source='event.id', read_only=True)
    number_of_tickets = serializers.IntegerField(source='ticket_count')
    timestamp = serializers.DateTimeField(source='booking_date', read_only=True)
    
    class Meta:
        model = Booking
        fields = [
            'booking_id', 'event_id', 'number_of_tickets', 
            'status', 'timestamp'
        ]


class AvailabilitySerializer(serializers.Serializer):
    """
    Serializer for event availability
    """
    event_id = serializers.CharField()
    available_tickets = serializers.IntegerField()
from rest_framework import serializers
from django.contrib.auth import get_user_model
from admin_app.models import Event

User = get_user_model()


class EventListSerializer(serializers.ModelSerializer):
    """Serializer for listing events with availability info for users"""
    event_id = serializers.CharField(source='id', read_only=True)
    available_tickets = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = [
            'event_id', 'name', 'venue', 'time', 'capacity', 
            'available_tickets', 'price_per_ticket', 'description'
        ]


class EventDetailSerializer(serializers.ModelSerializer):
    """Serializer for detailed event view for users"""
    event_id = serializers.CharField(source='id', read_only=True)
    available_tickets = serializers.ReadOnlyField()
    total_bookings = serializers.ReadOnlyField()
    utilization_percentage = serializers.ReadOnlyField()
    
    class Meta:
        model = Event
        fields = [
            'event_id', 'name', 'venue', 'time', 'capacity', 'available_tickets',
            'description', 'price_per_ticket', 'total_bookings', 
            'utilization_percentage', 'created_at'
        ]


class RegisterSerializer(serializers.ModelSerializer):
    """Public registration for normal users (non-staff, non-superuser)."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'address']

    def validate(self, attrs):
        # Force-safe flags regardless of any payload
        attrs['is_staff'] = False
        attrs['is_superuser'] = False
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        # Explicitly prevent privilege escalation
        validated_data.pop('is_staff', None)
        validated_data.pop('is_superuser', None)
        user = User(**validated_data)
        user.is_staff = False
        user.is_superuser = False
        user.set_password(password)
        user.save()
        return user


class StaffUserCreateSerializer(serializers.ModelSerializer):
    """Serializer for superuser to create staff users (non-superuser)."""
    password = serializers.CharField(write_only=True, min_length=8)

    class Meta:
        model = User
        fields = ['username', 'email', 'password', 'first_name', 'last_name', 'phone_number', 'address', 'is_staff']
        extra_kwargs = {
            'is_staff': {'required': True}
        }

    def validate(self, attrs):
        # Ensure staff flag is true and no superuser flag is allowed
        attrs['is_staff'] = bool(attrs.get('is_staff'))
        if not attrs['is_staff']:
            raise serializers.ValidationError('Staff users must have is_staff=True')
        return attrs

    def create(self, validated_data):
        password = validated_data.pop('password')
        is_staff = validated_data.pop('is_staff', True)
        user = User(**validated_data)
        user.is_staff = is_staff
        user.is_superuser = False
        user.set_password(password)
        user.save()
        return user

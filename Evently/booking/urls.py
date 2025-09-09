from django.urls import path
from . import views

urlpatterns = [
    # Book Ticket API
    path('bookings/', views.create_booking, name='create_booking'),
    
    # Cancel Booking API
    path('bookings/<str:booking_id>/', views.cancel_booking, name='cancel_booking'),
    
    # Booking History API
    path('users/<str:user_id>/bookings/', views.get_user_bookings, name='get_user_bookings'),
    
    # Check Availability API
    path('events/<str:event_id>/availability/', views.check_availability, name='check_availability'),
]

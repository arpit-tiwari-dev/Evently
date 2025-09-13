from celery import shared_task
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db import transaction
from django.db.models import F
from django.core.exceptions import ObjectDoesNotExist
import logging

from .models import Booking
from admin_app.models import Event

logger = logging.getLogger(__name__)


@shared_task
def process_booking_task(booking_id):
    """
    Process a booking asynchronously
    - Validate event availability
    - Update booking status
    - Send email notification
    """
    try:
        with transaction.atomic():
            # Get booking with lock
            booking = Booking.objects.select_for_update().get(id=booking_id)
            event = Event.objects.select_for_update().get(id=booking.event.id)
            
            logger.info(f"Processing booking {booking_id} for event {event.id}")
            
            # Check if event still has available tickets
            if event.available_tickets < booking.ticket_count:
                # Booking failed - insufficient tickets
                booking.status = 'failed'
                booking.save(update_fields=['status'])
                
                logger.warning(f"Booking {booking_id} failed: insufficient tickets")
                
                # Send failure email
                send_booking_email.delay(booking_id, 'failed')
                return f"Booking {booking_id} failed: insufficient tickets"
            
            # Booking successful
            booking.status = 'confirmed'
            booking.save(update_fields=['status'])
            
            logger.info(f"Booking {booking_id} confirmed successfully")
            
            # Send success email
            send_booking_email.delay(booking_id, 'confirmed')
            return f"Booking {booking_id} confirmed successfully"
            
    except ObjectDoesNotExist as e:
        logger.error(f"Booking or event not found: {booking_id} - {str(e)}")
        # Try to update booking status to failed if it exists
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.status = 'failed'
            booking.save(update_fields=['status'])
            send_booking_email.delay(booking_id, 'failed')
        except:
            pass
        return f"Booking {booking_id} failed: object not found"
        
    except Exception as e:
        logger.error(f"Unexpected error processing booking {booking_id}: {str(e)}")
        # Try to update booking status to failed if it exists
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.status = 'failed'
            booking.save(update_fields=['status'])
            send_booking_email.delay(booking_id, 'failed')
        except:
            pass
        return f"Booking {booking_id} failed: {str(e)}"


@shared_task
def send_booking_email(booking_id, status):
    """
    Send email notification for booking status
    """
    try:
        booking = Booking.objects.get(id=booking_id)
        user = booking.user
        event = booking.event
        
        # Email subject and template based on status
        if status == 'confirmed':
            subject = f"Booking Confirmed - {event.name}"
            template = 'emails/booking_confirmed.html'
        else:  # failed
            subject = f"Booking Failed - {event.name}"
            template = 'emails/booking_failed.html'
        
        # Email context
        context = {
            'user_name': user.get_full_name() or user.username,
            'event_name': event.name,
            'event_venue': event.venue,
            'event_time': event.time,
            'ticket_count': booking.ticket_count,
            'total_amount': booking.total_amount,
            'booking_id': booking_id,
        }
        
        # Render email content
        html_content = render_to_string(template, context)
        
        # Send email
        send_mail(
            subject=subject,
            message=f"Your booking for {event.name} has been {status}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"Email sent for booking {booking_id} with status {status}")
        return f"Email sent for booking {booking_id}"
        
    except Exception as e:
        logger.error(f"Failed to send email for booking {booking_id}: {str(e)}")
        return f"Email failed for booking {booking_id}: {str(e)}"

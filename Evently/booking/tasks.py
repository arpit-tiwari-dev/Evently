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
    logger.info(f"🚀 CELERY TASK STARTED: Processing booking {booking_id}")
    
    try:
        with transaction.atomic():
            # Get booking with lock
            logger.info(f"📋 Fetching booking {booking_id} from database")
            booking = Booking.objects.select_for_update().get(id=booking_id)
            event = Event.objects.select_for_update().get(id=booking.event.id)
            
            logger.info(f"✅ Booking {booking_id} found - Event: {event.name}, Requested tickets: {booking.ticket_count}")
            logger.info(f"📊 Event {event.id} - Available tickets: {event.available_tickets}, Capacity: {event.capacity}")
            
            # Check if event still has available tickets
            if event.available_tickets < booking.ticket_count:
                # Booking failed - insufficient tickets
                logger.warning(f"❌ INSUFFICIENT TICKETS: Booking {booking_id} - Available: {event.available_tickets}, Requested: {booking.ticket_count}")
                
                booking.status = 'failed'
                booking.save(update_fields=['status'])
                
                logger.info(f"💾 Booking {booking_id} status updated to 'failed'")
                
                # Invalidate availability cache
                from .concurrency_utils import EventAvailabilityManager
                EventAvailabilityManager.invalidate_event_cache(str(booking.event.id))
                
                # Send failure email
                logger.info(f"📧 Queuing failure email for booking {booking_id}")
                send_booking_email.delay(booking_id, 'failed')
                return f"Booking {booking_id} failed: insufficient tickets"
            
            # Booking successful
            logger.info(f"✅ BOOKING SUCCESS: Booking {booking_id} - Sufficient tickets available")
            
            booking.status = 'confirmed'
            booking.save(update_fields=['status'])
            
            logger.info(f"💾 Booking {booking_id} status updated to 'confirmed'")
            
            # Invalidate availability cache
            from .concurrency_utils import EventAvailabilityManager
            EventAvailabilityManager.invalidate_event_cache(str(booking.event.id))
            
            # Send success email
            logger.info(f"📧 Queuing success email for booking {booking_id}")
            send_booking_email.delay(booking_id, 'confirmed')
            
            logger.info(f"🎉 CELERY TASK COMPLETED: Booking {booking_id} confirmed successfully")
            return f"Booking {booking_id} confirmed successfully"
            
    except ObjectDoesNotExist as e:
        logger.error(f"❌ DATABASE ERROR: Booking or event not found: {booking_id} - {str(e)}")
        # Try to update booking status to failed if it exists
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.status = 'failed'
            booking.save(update_fields=['status'])
            logger.info(f"💾 Updated booking {booking_id} status to 'failed' due to object not found")
            send_booking_email.delay(booking_id, 'failed')
        except Exception as update_error:
            logger.error(f"❌ CRITICAL: Could not update booking {booking_id} status: {str(update_error)}")
        return f"Booking {booking_id} failed: object not found"
        
    except Exception as e:
        logger.error(f"❌ UNEXPECTED ERROR: Processing booking {booking_id}: {str(e)}", exc_info=True)
        # Try to update booking status to failed if it exists
        try:
            booking = Booking.objects.get(id=booking_id)
            booking.status = 'failed'
            booking.save(update_fields=['status'])
            logger.info(f"💾 Updated booking {booking_id} status to 'failed' due to unexpected error")
            send_booking_email.delay(booking_id, 'failed')
        except Exception as update_error:
            logger.error(f"❌ CRITICAL: Could not update booking {booking_id} status: {str(update_error)}")
        return f"Booking {booking_id} failed: {str(e)}"


@shared_task
def send_booking_email(booking_id, status):
    """
    Send email notification for booking status
    """
    logger.info(f"📧 EMAIL TASK STARTED: Sending {status} email for booking {booking_id}")
    
    try:
        booking = Booking.objects.get(id=booking_id)
        user = booking.user
        event = booking.event
        
        logger.info(f"📋 Email details - User: {user.email}, Event: {event.name}, Status: {status}")
        
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
        
        logger.info(f"📝 Rendering email template: {template}")
        # Render email content
        html_content = render_to_string(template, context)
        
        logger.info(f"📤 Sending email to {user.email} with subject: {subject}")
        # Send email
        send_mail(
            subject=subject,
            message=f"Your booking for {event.name} has been {status}.",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"✅ EMAIL SENT SUCCESSFULLY: Booking {booking_id} - {status} email sent to {user.email}")
        return f"Email sent for booking {booking_id}"
        
    except Exception as e:
        logger.error(f"❌ EMAIL FAILED: Booking {booking_id} - {str(e)}", exc_info=True)
        return f"Email failed for booking {booking_id}: {str(e)}"


@shared_task
def send_event_notification_email(user_id, event_id, notification_message, custom_subject=None):
    """
    Send event notification email to a specific user
    """
    logger.info(f"📧 EVENT NOTIFICATION EMAIL TASK STARTED: User {user_id}, Event {event_id}")
    
    try:
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        user = User.objects.get(id=user_id)
        event = Event.objects.get(id=event_id)
        
        logger.info(f"📋 Email details - User: {user.email}, Event: {event.name}")
        
        # Get user's booking for this event
        booking = Booking.objects.filter(event=event, user=user, status='confirmed').first()
        ticket_count = booking.ticket_count if booking else 0
        
        # Email subject and template
        if custom_subject:
            subject = custom_subject
        else:
            subject = f"Event Update - {event.name}"
        template = 'emails/event_notification.html'
        
        # Email context
        context = {
            'user_name': user.get_full_name() or user.username,
            'event_name': event.name,
            'event_venue': event.venue,
            'event_time': event.time,
            'ticket_count': ticket_count,
            'notification_message': notification_message,
        }
        
        logger.info(f"📝 Rendering email template: {template}")
        # Render email content
        html_content = render_to_string(template, context)
        
        logger.info(f"📤 Sending notification email to {user.email}")
        # Send email
        send_mail(
            subject=subject,
            message=f"Event Update for {event.name}: {notification_message}",
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            html_message=html_content,
            fail_silently=False,
        )
        
        logger.info(f"✅ EVENT NOTIFICATION EMAIL SENT SUCCESSFULLY: User {user_id}, Event {event_id}")
        return f"Event notification email sent to user {user_id} for event {event_id}"
        
    except Exception as e:
        logger.error(f"❌ EVENT NOTIFICATION EMAIL FAILED: User {user_id}, Event {event_id} - {str(e)}", exc_info=True)
        return f"Event notification email failed for user {user_id}, event {event_id}: {str(e)}"
import logging
from django.db import connection, transaction
from django.utils import timezone
from bookings.models import Booking
from events.models import Event

logger = logging.getLogger(__name__)

def expire_booking(booking_id: str) -> bool:
    """
    Service function to expire a pending booking and restore event inventory.
    
    Requirements satisfied:
    - Executed inside transaction.atomic().
    - Verifies booking exists.
    - Verifies status == "Pending Payment".
    - Verifies expires_at <= timezone.now().
    - Restores event seats atomically.
    - Sets booking status = "Expired".
    - Saves changes safely using specific update_fields.
    - Highly idempotent: safe if executed multiple times or concurrently.
    
    Args:
        booking_id (str): The unique booking_id (e.g., 'EVH-XXXXXXXX') of the booking.
        
    Returns:
        bool: True if the booking transitioned to Expired during this execution,
              False if already expired, confirmed, or not yet eligible for expiration.
    """
    with transaction.atomic():
        # Query booking with row-level locking if supported by the database engine (PostgreSQL/MySQL)
        booking_qs = Booking.objects.select_related('event')
        if connection.features.has_select_for_update:
            booking_qs = booking_qs.select_for_update(nowait=True)
            
        try:
            booking = booking_qs.get(booking_id=booking_id)
        except Booking.DoesNotExist:
            logger.warning(f"expire_booking called for non-existent booking ID: {booking_id}")
            return False
        except Exception as e:
            # Captures OperationalError/DatabaseError if lock cannot be acquired immediately
            logger.error(f"Lock contention: could not acquire lock for booking {booking_id}: {e}")
            raise

        # Idempotency & Lifecycle Verification:
        if booking.status == 'Expired':
            logger.info(f"Booking {booking_id} is already Expired (idempotent no-op).")
            return False

        if booking.status != 'Pending Payment':
            logger.warning(
                f"Booking {booking_id} has terminal or active status '{booking.status}'. Skipping expiration."
            )
            return False

        if not booking.expires_at or booking.expires_at > timezone.now():
            logger.info(
                f"Booking {booking_id} has not reached expiration threshold ({booking.expires_at})."
            )
            return False

        # Acquire lock on the parent Event record to safely restore seat inventory
        event_qs = Event.objects.filter(pk=booking.event_id)
        if connection.features.has_select_for_update:
            event_qs = event_qs.select_for_update(nowait=True)
            
        try:
            event = event_qs.get()
        except Exception as e:
            logger.error(
                f"Lock contention: could not acquire lock for event {booking.event_id} while expiring booking {booking_id}: {e}"
            )
            raise

        # Restore seat inventory
        event.available_seats += booking.quantity
        event.save(update_fields=['available_seats', 'updated_at'])

        # Update booking status
        booking.status = 'Expired'
        booking.save(update_fields=['status'])

        logger.info(
            f"Successfully expired booking {booking_id} and restored {booking.quantity} seats to event '{event.title}'."
        )
        return True

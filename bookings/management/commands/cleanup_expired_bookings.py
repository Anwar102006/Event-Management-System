import logging
from django.core.management.base import BaseCommand
from django.utils import timezone
from bookings.models import Booking
from bookings.services import expire_booking

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Scans for expired Pending Payment bookings in chunked batches and restores event inventory.'

    def handle(self, *args, **options):
        batch_size = 100
        total_processed = 0
        total_expired = 0
        total_failed = 0
        failed_ids = set()

        self.stdout.write(self.style.NOTICE("Starting cleanup of expired reservations..."))

        while True:
            # Leverage existing composite index (status, expires_at)
            # Exclude persistently failing booking IDs during this execution cycle to prevent infinite loops
            queryset = Booking.objects.filter(
                status='Pending Payment',
                expires_at__lte=timezone.now()
            )
            if failed_ids:
                queryset = queryset.exclude(booking_id__in=failed_ids)

            # Query values_list of booking_ids in chunks of batch_size (100) to optimize memory usage
            expired_booking_ids = list(
                queryset.order_by('expires_at')
                .values_list('booking_id', flat=True)[:batch_size]
            )

            if not expired_booking_ids:
                break

            for booking_id in expired_booking_ids:
                total_processed += 1
                try:
                    was_expired = expire_booking(booking_id)
                    if was_expired:
                        total_expired += 1
                        self.stdout.write(self.style.SUCCESS(f"✔ Expired booking: {booking_id}"))
                except Exception as e:
                    total_failed += 1
                    failed_ids.add(booking_id)
                    logger.error(f"Error expiring booking {booking_id}: {e}", exc_info=True)
                    self.stdout.write(self.style.ERROR(f"✖ Failed to expire booking {booking_id}: {e}"))

            # If fewer than batch_size records were returned, all current eligible records have been processed
            if len(expired_booking_ids) < batch_size:
                break

        summary_msg = (
            f"Cleanup complete. Processed: {total_processed} | "
            f"Expired: {total_expired} | Failed: {total_failed}"
        )
        logger.info(summary_msg)
        if total_failed > 0:
            self.stdout.write(self.style.WARNING(summary_msg))
        else:
            self.stdout.write(self.style.SUCCESS(summary_msg))

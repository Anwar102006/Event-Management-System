import uuid
import os
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.db import models
from accounts.models import User
from events.models import Event

class Booking(models.Model):
    STATUS_CHOICES = (
        ('Pending Payment', 'Pending Payment'),
        ('Payment Processing', 'Payment Processing'),
        ('Confirmed', 'Confirmed'),
        ('Cancelled', 'Cancelled'),
        ('Expired', 'Expired'),
        ('Attended', 'Attended'),
        ('Refunded', 'Refunded'),
    )

    booking_id = models.CharField(max_length=20, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookings')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='bookings')
    quantity = models.PositiveIntegerField(default=1)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    booking_date = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending Payment')
    qr_code_image = models.ImageField(upload_to='qrcodes/', blank=True, null=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['-booking_date']
        indexes = [
            models.Index(fields=['status', 'expires_at'], name='booking_expiry_idx'),
        ]

    def __str__(self):
        return f"{self.booking_id} - {self.user.username} @ {self.event.title}"

    def save(self, *args, **kwargs):
        if not self.booking_id:
            self.booking_id = 'EVH-' + str(uuid.uuid4()).upper()[:8]
        super().save(*args, **kwargs)
        if not self.qr_code_image:
            self._generate_qr()

    def _generate_qr(self):
        """Generate QR code image containing booking verification data."""
        qr_data = (
            f"EVENTHUB_TICKET\n"
            f"BookingID: {self.booking_id}\n"
            f"UserID: {self.user.id}\n"
            f"EventID: {self.event.id}\n"
            f"Event: {self.event.title}\n"
            f"Qty: {self.quantity}\n"
            f"Status: {self.status}"
        )
        qr = qrcode.QRCode(version=1, box_size=10, border=4)
        qr.add_data(qr_data)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buf = BytesIO()
        img.save(buf, format='PNG')
        file_name = f"qr_{self.booking_id}.png"
        self.qr_code_image.save(file_name, ContentFile(buf.getvalue()), save=True)

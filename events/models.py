from django.db import models
from django.utils import timezone
from accounts.models import User

class Event(models.Model):
    CATEGORY_CHOICES = (
        ('Technology', 'Technology'),
        ('Music', 'Music'),
        ('Sports', 'Sports'),
        ('Cultural', 'Cultural'),
        ('Workshops', 'Workshops'),
        ('Business', 'Business'),
        ('Education', 'Education'),
    )
    STATUS_CHOICES = (
        ('Upcoming', 'Upcoming'),
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Cancelled', 'Cancelled'),
    )

    title = models.CharField(max_length=200)
    description = models.TextField()
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    organizer = models.ForeignKey(User, on_delete=models.CASCADE, related_name='organized_events')
    banner = models.ImageField(upload_to='banners/', blank=True, null=True)
    date_time = models.DateTimeField()
    venue = models.CharField(max_length=300)
    google_maps_link = models.URLField(blank=True, null=True)
    max_seats = models.PositiveIntegerField()
    available_seats = models.PositiveIntegerField()
    ticket_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='Upcoming')
    is_approved = models.BooleanField(default=False)
    wishlisted_by = models.ManyToManyField(User, blank=True, related_name='wishlist_events')
    recently_viewed_by = models.ManyToManyField(User, blank=True, related_name='recently_viewed_events')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def is_sold_out(self):
        return self.available_seats == 0

    def average_rating(self):
        reviews = self.reviews.all()
        if reviews.exists():
            return round(sum(r.rating for r in reviews) / reviews.count(), 1)
        return None

    def booking_count(self):
        return self.bookings.filter(status='Confirmed').count()

    def update_status(self):
        now = timezone.now()
        if self.date_time > now:
            self.status = 'Upcoming'
        elif self.date_time <= now:
            self.status = 'Ongoing'
        self.save()

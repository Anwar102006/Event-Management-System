from django.db import models
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('organizer', 'Organizer'),
        ('user', 'User'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    is_email_verified = models.BooleanField(default=False)
    profile_picture = models.ImageField(upload_to='profiles/', blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    phone_number = models.CharField(max_length=15, blank=True, null=True)

    def is_admin(self):
        return self.role == 'admin' or self.is_superuser

    def is_organizer(self):
        return self.role == 'organizer'

    def is_regular_user(self):
        return self.role == 'user'

    def __str__(self):
        return f"{self.username} ({self.get_role_display()})"

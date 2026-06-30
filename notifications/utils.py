from .models import Notification

def create_notification(user, title, message):
    """Helper to create a notification for a user."""
    Notification.objects.create(user=user, title=title, message=message)

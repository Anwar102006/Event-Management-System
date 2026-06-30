"""
Seed script to create demo users (admin, organizer, user) and sample events.
Run with: python manage.py shell < seed_data.py
Or: python seed_data.py (ensure Django is configured)
"""
import os
import sys
import django

# Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'event_management_system.settings')
django.setup()

from django.utils import timezone
from datetime import timedelta
from accounts.models import User
from events.models import Event

# ── Create Users ──────────────────────────────────────────────────────────────
print("Creating demo users...")

admin_user, _ = User.objects.get_or_create(username='admin')
admin_user.set_password('admin123')
admin_user.role = 'admin'
admin_user.is_staff = True
admin_user.is_superuser = True
admin_user.email = 'admin@eventhub.com'
admin_user.first_name = 'System'
admin_user.last_name = 'Admin'
admin_user.is_email_verified = True
admin_user.save()
print(f"  [OK] Admin user: admin / admin123")

organizer_user, _ = User.objects.get_or_create(username='organizer1')
organizer_user.set_password('org123')
organizer_user.role = 'organizer'
organizer_user.email = 'organizer@eventhub.com'
organizer_user.first_name = 'Arjun'
organizer_user.last_name = 'Mehta'
organizer_user.is_email_verified = True
organizer_user.save()
print(f"  [OK] Organizer: organizer1 / org123")

regular_user, _ = User.objects.get_or_create(username='user1')
regular_user.set_password('user123')
regular_user.role = 'user'
regular_user.email = 'user@eventhub.com'
regular_user.first_name = 'Sarah'
regular_user.last_name = 'Rogers'
regular_user.is_email_verified = True
regular_user.save()
print(f"  [OK] Regular user: user1 / user123")

# ── Create Sample Events ──────────────────────────────────────────────────────
print("\nCreating sample events...")

sample_events = [
    {
        'title': 'AI & Machine Learning Summit 2026',
        'description': 'Join industry experts for an immersive two-day summit covering the latest trends in artificial intelligence and machine learning. Sessions include hands-on workshops, keynote speeches from Google, OpenAI and more.',
        'category': 'Technology',
        'date_time': timezone.now() + timedelta(days=14),
        'venue': 'Convention Center, Mumbai',
        'max_seats': 500,
        'ticket_price': 89.99,
    },
    {
        'title': 'Classical Symphony Night: Beethoven & Mozart',
        'description': 'An evening of world-class classical music performed by the National Symphony Orchestra. Dress code: smart casual.',
        'category': 'Music',
        'date_time': timezone.now() + timedelta(days=7),
        'venue': 'Royal Concert Hall, Delhi',
        'max_seats': 1200,
        'ticket_price': 45.00,
    },
    {
        'title': 'Startup Founders Bootcamp',
        'description': 'A 3-day intensive workshop for early-stage startup founders covering product-market fit, fundraising, pitch deck design, and building your first team.',
        'category': 'Workshops',
        'date_time': timezone.now() + timedelta(days=21),
        'venue': 'Innovation Hub, Bengaluru',
        'max_seats': 100,
        'ticket_price': 149.00,
    },
    {
        'title': 'National Football Championship Finals',
        'description': 'Watch the best football teams battle it out for the national championship. Live commentary, food stalls, and exciting halftime shows.',
        'category': 'Sports',
        'date_time': timezone.now() + timedelta(days=30),
        'venue': 'National Stadium, Chennai',
        'max_seats': 30000,
        'ticket_price': 25.00,
    },
    {
        'title': 'Traditional Kuchipudi Dance Festival',
        'description': 'A grand celebration of Indian classical dance forms featuring renowned artists performing Kuchipudi, Bharatanatyam, and Odissi in a stunning heritage venue.',
        'category': 'Cultural',
        'date_time': timezone.now() + timedelta(days=10),
        'venue': 'Kalakshetra, Chennai',
        'max_seats': 800,
        'ticket_price': 30.00,
    },
    {
        'title': 'Digital Marketing Masterclass',
        'description': 'Learn the art of digital marketing from seasoned professionals. Topics include SEO, social media advertising, content strategy, email marketing, and analytics dashboards.',
        'category': 'Education',
        'date_time': timezone.now() + timedelta(days=5),
        'venue': 'Webinar + Hyderabad Campus',
        'max_seats': 300,
        'ticket_price': 0.00,
    },
    {
        'title': 'Blockchain for Business Leaders',
        'description': 'An executive-level conference exploring how blockchain technology is revolutionizing supply chains, finance, healthcare, and government. Panel discussions and live demos.',
        'category': 'Business',
        'date_time': timezone.now() + timedelta(days=18),
        'venue': 'Business District, Pune',
        'max_seats': 200,
        'ticket_price': 199.00,
    },
]

for ev_data in sample_events:
    event, created = Event.objects.get_or_create(
        title=ev_data['title'],
        defaults={
            **ev_data,
            'organizer': organizer_user,
            'available_seats': ev_data['max_seats'],
            'is_approved': True,
            'google_maps_link': 'https://maps.google.com',
            'status': 'Upcoming',
        }
    )
    if created:
        print(f"  [OK] Event: {event.title}")
    else:
        print(f"  [info] Already exists: {event.title}")

print("\n[OK] Seed data created successfully!")
print("\nDemo Credentials:")
print("   Admin:     admin / admin123")
print("   Organizer: organizer1 / org123")
print("   User:      user1 / user123")
print("\nRun the server: python manage.py runserver")
print("   Then open:  http://127.0.0.1:8000/")

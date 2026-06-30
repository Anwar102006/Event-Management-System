from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from events.models import Event
from django.shortcuts import render

def landing_view(request):
    featured_events = Event.objects.filter(is_approved=True).order_by('-created_at')[:6]
    return render(request, 'landing.html', {'featured_events': featured_events})

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', landing_view, name='landing'),
    path('accounts/', include('accounts.urls', namespace='accounts')),
    path('events/', include('events.urls', namespace='events')),
    path('bookings/', include('bookings.urls', namespace='bookings')),
    path('reviews/', include('reviews.urls', namespace='reviews')),
    path('dashboard/', include('dashboard.urls', namespace='dashboard')),
    path('payments/', include('payments.urls', namespace='payments')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

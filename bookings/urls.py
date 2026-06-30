from django.urls import path
from . import views

app_name = 'bookings'

urlpatterns = [
    path('checkout/<int:event_pk>/', views.checkout_view, name='checkout'),
    path('confirmation/<int:pk>/', views.booking_confirmation_view, name='confirmation'),
    path('download/<int:pk>/', views.download_ticket_pdf, name='download_ticket'),
    path('cancel/<int:pk>/', views.cancel_booking_view, name='cancel'),
    path('checkin/', views.checkin_view, name='checkin'),
    path('certificate/<int:pk>/', views.download_certificate_pdf, name='download_certificate'),
]

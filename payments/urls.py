from django.urls import path
from . import views

app_name = 'payments'

urlpatterns = [
    path('invoice/<str:booking_id>/', views.invoice_detail_view, name='invoice'),
    path('invoice/<str:booking_id>/download/', views.download_receipt_pdf, name='download_receipt'),
]

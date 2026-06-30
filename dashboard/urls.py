from django.urls import path
from . import views

app_name = 'dashboard'

urlpatterns = [
    path('', views.dashboard_view, name='dashboard'),
    path('organizer/', views.organizer_dashboard_view, name='organizer'),
    path('admin/', views.admin_dashboard_view, name='admin'),
    path('admin/approve/<int:pk>/', views.approve_event_view, name='approve_event'),
    path('admin/reject/<int:pk>/', views.reject_event_view, name='reject_event'),
    path('admin/toggle-user/<int:pk>/', views.toggle_user_active_view, name='toggle_user'),
    path('admin/delete-user/<int:pk>/', views.delete_user_view, name='delete_user'),
    path('admin/export/csv/', views.export_report_csv, name='export_csv'),
    path('admin/export/pdf/', views.export_report_pdf, name='export_pdf'),
    path('organizer/export/<int:event_pk>/', views.export_attendees_csv, name='export_attendees'),
    path('notifications/read/', views.mark_notifications_read, name='mark_read'),
]

from django.urls import path
from . import views

app_name = 'events'

urlpatterns = [
    path('', views.event_list_view, name='list'),
    path('<int:pk>/', views.event_detail_view, name='detail'),
    path('create/', views.event_create_view, name='create'),
    path('<int:pk>/edit/', views.event_edit_view, name='edit'),
    path('<int:pk>/delete/', views.event_delete_view, name='delete'),
    path('<int:pk>/wishlist/', views.toggle_wishlist_view, name='wishlist'),
]

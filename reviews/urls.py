from django.urls import path
from . import views

app_name = 'reviews'

urlpatterns = [
    path('submit/<int:event_pk>/', views.submit_review_view, name='submit'),
    path('<int:review_pk>/like/', views.like_review_view, name='like'),
]

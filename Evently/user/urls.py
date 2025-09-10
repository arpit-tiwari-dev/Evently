from django.urls import path
from . import views

urlpatterns = [
    # User Event APIs
    path('events/', views.EventListView.as_view(), name='user_list_events'),
    path('events/<str:event_id>/', views.get_event_details, name='user_get_event_details'),
    # Auth APIs
    path('auth/register/', views.register, name='register'),
    path('auth/login/', views.login, name='login'),
    path('auth/logout/', views.logout, name='logout'),
    path('auth/me/', views.me, name='me'),
]

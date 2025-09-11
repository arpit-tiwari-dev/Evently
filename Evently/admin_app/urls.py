from django.urls import path
from . import views

urlpatterns = [
    # Event Management APIs
    path('events/', views.create_event, name='create_event'),
    # Place static paths BEFORE the dynamic <event_id> matcher to avoid collisions
    path('events/list/', views.EventListView.as_view(), name='list_events'),
    path('events/<str:event_id>/details/', views.get_event_details, name='get_event_details'),
    path('events/<str:event_id>/notify/', views.notify_users, name='notify_users'),
    path('events/<str:event_id>/', views.update_event, name='update_event'),
    path('events/<str:event_id>/delete/', views.delete_event, name='delete_event'),
    
    # Analytics APIs
    path('analytics/', views.get_analytics, name='get_analytics'),
    path('analytics/<str:event_id>/', views.get_event_analytics, name='get_event_analytics'),
    
    # User management (superuser only)
    path('users/staff/', views.create_staff_user, name='create_staff_user'),
    path('users/bulk_delete/', views.bulk_delete_test_users, name='bulk_delete_test_users'),
]

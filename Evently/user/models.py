from django.contrib.auth.models import AbstractUser
from django.db import models

class User(AbstractUser):
    # Add your extra fields here
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Critical indexes for user performance
            models.Index(fields=['email'], name='user_email_idx'),
            models.Index(fields=['username'], name='user_username_idx'),
            models.Index(fields=['is_staff'], name='user_staff_idx'),
            models.Index(fields=['is_active'], name='user_active_idx'),
            models.Index(fields=['created_at'], name='user_created_idx'),
            # Composite indexes for common queries
            models.Index(fields=['is_staff', 'is_active'], name='user_staff_active_idx'),
            models.Index(fields=['email', 'is_active'], name='user_email_active_idx'),
        ]

    def __str__(self):
        return self.username
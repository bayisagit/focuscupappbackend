from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('MEMBER', 'Fellowship Member'),
        ('MANAGER', 'Tournament & Fellowship Manager'),
    ]

    email = models.EmailField(unique=True, verbose_name="Email Address")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    USERNAME_FIELD = 'username'
    REQUIRED_FIELDS = ['email']

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_manager(self):
        return self.role == 'MANAGER' or self.is_staff or self.is_superuser

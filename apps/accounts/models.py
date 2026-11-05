from django.db import models
from django.contrib.auth.models import AbstractUser

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('MEMBER', 'Fellowship Member'),
        ('COACH', 'Batch Coach'),
        ('MANAGER', 'Tournament & Fellowship Manager'),
    ]

    email = models.EmailField(unique=True, verbose_name="Email Address")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='MEMBER')
    linked_member = models.ForeignKey(
        'members.MemberProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coach_accounts',
        help_text="The registered fellowship member identity behind this coach account"
    )
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

    @property
    def is_coach(self):
        return self.role == 'COACH' or hasattr(self, 'coached_batch_team')

    def get_coached_batch_team(self):
        if hasattr(self, 'coached_batch_team') and self.coached_batch_team:
            return self.coached_batch_team
        return self.coached_teams.first() if hasattr(self, 'coached_teams') else None

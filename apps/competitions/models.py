from django.db import models
from django.conf import settings
from apps.members.constants import COMPETING_BATCH_CHOICES

class Season(models.Model):
    STATUS_CHOICES = [
        ('UPCOMING', 'Upcoming'),
        ('REGISTRATION_OPEN', 'Registration Open'),
        ('ONGOING', 'Ongoing / In Progress'),
        ('COMPLETED', 'Completed'),
        ('ARCHIVED', 'Archived'),
    ]

    name = models.CharField(max_length=150, help_text="e.g. Focus Football Cup - 2026/27")
    academic_year = models.CharField(max_length=50, help_text="e.g. 2026/2027")
    semester = models.CharField(max_length=50, default="Semester 1")
    start_date = models.DateField()
    end_date = models.DateField()
    registration_start = models.DateField(null=True, blank=True)
    registration_end = models.DateField(null=True, blank=True)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='UPCOMING')
    is_active = models.BooleanField(default=False, help_text="Designates the current active tournament season")
    rules = models.TextField(
        blank=True,
        default=(
            "Central Motto: 'Winning is a bonus; friendship, joy, and fellowship come first!'\n"
            "Format: Single round-robin between eligible academic batches (2nd, 3rd, 4th, 5th Years).\n"
            "Scoring: Win = 3 pts, Draw = 1 pt, Loss = 0 pts.\n"
            "Fair play, Christ-centered sportsmanship, and unity are honored above all else."
        )
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-start_date', '-created_at']
        verbose_name = 'Competition Season'
        verbose_name_plural = 'Competition Seasons'

    def __str__(self):
        return f"{self.name} ({self.academic_year} - {self.semester})"

    def save(self, *args, **kwargs):
        # If this season is set to active, deactivate all other seasons
        if self.is_active:
            Season.objects.exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)


class BatchTeam(models.Model):
    batch_code = models.CharField(
        max_length=20,
        choices=COMPETING_BATCH_CHOICES,
        unique=True,
        help_text="The academic batch this team represents"
    )
    name = models.CharField(max_length=100, help_text="e.g. 2nd Year Batch")
    nickname = models.CharField(max_length=100, blank=True, default='', help_text="e.g. Joyful Warriors")
    color_hex = models.CharField(max_length=10, default='#10B981')
    logo = models.ImageField(upload_to='batch_logos/', null=True, blank=True)
    logo_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Cloudinary CDN URL for batch crest/logo"
    )
    team_photo = models.ImageField(upload_to='batch_photos/', null=True, blank=True)
    team_photo_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Cloudinary CDN URL for batch team/group photo"
    )
    motto = models.CharField(max_length=255, blank=True, default="United in Christ, Strong in Fellowship")
    description = models.TextField(blank=True, default='')
    is_competing = models.BooleanField(
        default=True,
        help_text="False for 'Other' community fellowship group; True for 2nd, 3rd, 4th, 5th year teams"
    )
    coach_user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coached_batch_team',
        help_text="Dedicated coach user login account for this batch team"
    )
    coach_member = models.ForeignKey(
        'members.MemberProfile',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='coached_batch_teams',
        help_text="The registered fellowship member appointed as coach for this batch"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['batch_code']
        verbose_name = 'Batch Team'
        verbose_name_plural = 'Batch Teams'

    def __str__(self):
        return f"{self.name} ({self.get_batch_code_display()})"

    @property
    def photo_url(self):
        if self.team_photo_url and str(self.team_photo_url).strip():
            return str(self.team_photo_url).strip()
        if self.team_photo:
            try:
                return self.team_photo.url
            except Exception:
                return str(self.team_photo)
        if self.logo_url and str(self.logo_url).strip():
            return str(self.logo_url).strip()
        if self.logo:
            try:
                return self.logo.url
            except Exception:
                return str(self.logo)
        return None


class SeasonTeam(models.Model):
    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='season_teams')
    batch_team = models.ForeignKey(BatchTeam, on_delete=models.CASCADE, related_name='participating_seasons')
    registered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('season', 'batch_team')
        verbose_name = 'Season Participating Team'
        verbose_name_plural = 'Season Participating Teams'

    def __str__(self):
        return f"{self.batch_team.name} in {self.season.name}"

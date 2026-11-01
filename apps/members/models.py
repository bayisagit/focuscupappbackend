from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.members.constants import (
    COLLEGE_CHOICES,
    ALL_DEPARTMENTS,
    ALL_YEARS,
    FELLOWSHIP_TEAMS,
    GENDER_CHOICES,
    FOOTBALL_POSITIONS,
    COMPETING_BATCH_CHOICES,
    validate_academic_eligibility,
)
from apps.competitions.models import Season, BatchTeam


class MemberProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='profile'
    )
    first_name = models.CharField(max_length=100)
    second_name = models.CharField(max_length=100)
    college = models.CharField(max_length=50, choices=COLLEGE_CHOICES)
    department = models.CharField(max_length=100, choices=ALL_DEPARTMENTS)
    academic_year = models.CharField(max_length=50, choices=ALL_YEARS)
    fellowship_team = models.CharField(max_length=100, choices=FELLOWSHIP_TEAMS)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)

    # Football Identity
    primary_position = models.CharField(
        max_length=50,
        choices=FOOTBALL_POSITIONS,
        blank=True,
        null=True,
        help_text="Primary football position on the pitch"
    )
    secondary_position = models.CharField(
        max_length=50,
        choices=FOOTBALL_POSITIONS,
        blank=True,
        null=True
    )
    preferred_jersey_number = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Desired squad jersey number"
    )
    profile_picture = models.ImageField(upload_to='profiles/', null=True, blank=True)
    profile_picture_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Cloudinary CDN URL for profile photo"
    )
    jersey_picture = models.ImageField(upload_to='jerseys/', null=True, blank=True)
    bio = models.TextField(blank=True, default='')
    personal_chant = models.CharField(
        max_length=255,
        blank=True,
        default='',
        help_text="Personal faith or football motto (e.g. 'Playing for His Glory', 'Jesus Is My Savior')"
    )

    # Community metrics
    followers_count = models.PositiveIntegerField(default=0)
    following_count = models.PositiveIntegerField(default=0)

    # Administrative and eligibility flags
    is_approved = models.BooleanField(default=True)
    is_suspended = models.BooleanField(default=False)
    is_football_eligible = models.BooleanField(
        default=False,
        help_text="Determined automatically by academic department, college and year"
    )
    competing_batch = models.CharField(
        max_length=20,
        choices=COMPETING_BATCH_CHOICES,
        null=True,
        blank=True,
        help_text="The official competing batch roster the member qualifies for"
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['first_name', 'second_name']
        verbose_name = 'Member Profile'
        verbose_name_plural = 'Member Profiles'

    def __str__(self):
        return f"{self.full_name} ({self.get_college_display()} - {self.academic_year})"

    @property
    def full_name(self):
        return f"{self.first_name} {self.second_name}".strip()

    @property
    def avatar_url(self):
        if self.profile_picture_url:
            return self.profile_picture_url
        if self.profile_picture:
            try:
                return self.profile_picture.url
            except Exception:
                return str(self.profile_picture)
        return None

    def clean(self):
        super().clean()
        is_valid, err_msg, is_eligible, batch = validate_academic_eligibility(
            self.college, self.department, self.academic_year
        )
        if not is_valid:
            raise ValidationError({'department': err_msg or "Invalid college/department/year combination."})

        self.is_football_eligible = is_eligible
        self.competing_batch = batch

    def save(self, *args, **kwargs):
        is_valid, _, is_eligible, batch = validate_academic_eligibility(
            self.college, self.department, self.academic_year
        )
        if is_valid:
            self.is_football_eligible = is_eligible
            self.competing_batch = batch
        super().save(*args, **kwargs)


class MemberFollow(models.Model):
    follower = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='following_relations'
    )
    following = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='follower_relations'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')
        ordering = ['-created_at']
        verbose_name = 'Member Follow'
        verbose_name_plural = 'Member Follows'

    def clean(self):
        if self.follower_id == self.following_id:
            raise ValidationError("A member cannot follow themselves.")

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class PlayerRegistration(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending Manager Review'),
        ('APPROVED', 'Approved for Tournament Squad'),
        ('REJECTED', 'Rejected'),
    ]

    member = models.ForeignKey(
        MemberProfile,
        on_delete=models.CASCADE,
        related_name='player_registrations'
    )
    season = models.ForeignKey(
        Season,
        on_delete=models.CASCADE,
        related_name='player_registrations'
    )
    batch_team = models.ForeignKey(
        BatchTeam,
        on_delete=models.CASCADE,
        related_name='roster_players'
    )
    preferred_position = models.CharField(max_length=50, choices=FOOTBALL_POSITIONS)
    jersey_number = models.PositiveSmallIntegerField(help_text="Registered jersey number for this season")
    jersey_photo = models.ImageField(upload_to='roster_jerseys/', null=True, blank=True)
    football_notes = models.CharField(max_length=255, blank=True, default='')

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reviewed_player_registrations'
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True, default='')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('member', 'season')
        ordering = ['-created_at']
        verbose_name = 'Player Tournament Registration'
        verbose_name_plural = 'Player Tournament Registrations'

    def clean(self):
        # Strict validation: Member must be football eligible and batch team must match competing batch
        if not self.member.is_football_eligible:
            raise ValidationError("This member is not eligible for tournament football rosters.")

        if self.member.competing_batch != self.batch_team.batch_code:
            raise ValidationError(
                f"Member's academic batch '{self.member.get_competing_batch_display()}' "
                f"does not match team batch '{self.batch_team.name}'."
            )

    def __str__(self):
        return f"{self.member.full_name} (#{self.jersey_number}) - {self.batch_team.name} ({self.status})"

from django.db import models
from django.conf import settings
from django.core.exceptions import ValidationError
from apps.competitions.models import Season, BatchTeam
from apps.members.models import MemberProfile


class Match(models.Model):
    STATUS_CHOICES = [
        ('SCHEDULED', 'Scheduled'),
        ('LIVE', 'Live'),
        ('HALF_TIME', 'Half Time'),
        ('COMPLETED', 'Completed'),
        ('POSTPONED', 'Postponed'),
        ('CANCELLED', 'Cancelled'),
    ]

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='matches')
    round_number = models.PositiveSmallIntegerField(default=1)
    home_team = models.ForeignKey(BatchTeam, on_delete=models.CASCADE, related_name='home_matches')
    away_team = models.ForeignKey(BatchTeam, on_delete=models.CASCADE, related_name='away_matches')

    match_date = models.DateField()
    kick_off_time = models.TimeField()
    venue = models.CharField(max_length=150, default="AASTU Main Football Field")

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='SCHEDULED')
    home_score = models.PositiveSmallIntegerField(default=0)
    away_score = models.PositiveSmallIntegerField(default=0)

    is_published = models.BooleanField(
        default=False,
        help_text="Only published and completed matches count towards official standings and player statistics"
    )

    match_report = models.TextField(blank=True, default='')
    player_of_the_match = models.ForeignKey(
        MemberProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='potm_awards'
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='created_matches'
    )
    updated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='updated_matches'
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['match_date', 'kick_off_time']
        verbose_name = 'Match'
        verbose_name_plural = 'Matches'

    def clean(self):
        super().clean()
        if self.home_team_id == self.away_team_id:
            raise ValidationError("Home team and away team cannot be the same batch.")

    def __str__(self):
        score_str = f"{self.home_score} - {self.away_score}" if self.status in ('LIVE', 'HALF_TIME', 'COMPLETED') else "vs"
        return f"{self.home_team.name} {score_str} {self.away_team.name} ({self.match_date})"


class MatchSquad(models.Model):
    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='squad')
    team = models.ForeignKey(BatchTeam, on_delete=models.CASCADE, related_name='match_squad_entries')
    player = models.ForeignKey(MemberProfile, on_delete=models.CASCADE, related_name='match_appearances')
    jersey_number = models.PositiveSmallIntegerField()
    is_starter = models.BooleanField(default=True)
    is_goalkeeper = models.BooleanField(default=False)

    class Meta:
        unique_together = ('match', 'player')
        verbose_name = 'Match Squad Selection'
        verbose_name_plural = 'Match Squad Selections'

    def clean(self):
        if self.team_id not in (self.match.home_team_id, self.match.away_team_id):
            raise ValidationError("Selected team is not participating in this match.")
        if self.player.competing_batch != self.team.batch_code:
            raise ValidationError(
                f"Player {self.player.full_name} belongs to batch {self.player.get_competing_batch_display()}, "
                f"not {self.team.name}."
            )

    def __str__(self):
        role = "GK" if self.is_goalkeeper else ("Starter" if self.is_starter else "Sub")
        return f"{self.player.full_name} (#{self.jersey_number}) [{role}] - {self.team.name}"


class MatchEvent(models.Model):
    EVENT_TYPES = [
        ('GOAL', 'Goal Scored'),
        ('ASSIST', 'Goal Assist'),
        ('OWN_GOAL', 'Own Goal (Against Own Team)'),
        ('YELLOW_CARD', 'Yellow Card'),
        ('RED_CARD', 'Red Card'),
        ('SUBSTITUTION', 'Substitution'),
        ('MATCH_START', 'Match Kick-off'),
        ('HALF_TIME', 'Half Time Whistle'),
        ('SECOND_HALF', 'Second Half Kick-off'),
        ('FULL_TIME', 'Full Time Whistle'),
        ('NOTE', 'Match Incident / Note'),
    ]

    match = models.ForeignKey(Match, on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    team = models.ForeignKey(BatchTeam, on_delete=models.CASCADE, related_name='team_events')
    player = models.ForeignKey(
        MemberProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='match_events'
    )
    related_player = models.ForeignKey(
        MemberProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='related_match_events',
        help_text="Assisting player or substituted player"
    )
    minute = models.PositiveSmallIntegerField(default=1)
    extra_minute = models.PositiveSmallIntegerField(null=True, blank=True)
    description = models.CharField(max_length=255, blank=True, default='')

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['minute', 'extra_minute', 'created_at']
        verbose_name = 'Match Event'
        verbose_name_plural = 'Match Events'

    def clean(self):
        super().clean()
        if self.team_id not in (self.match.home_team_id, self.match.away_team_id):
            raise ValidationError("Event team must be either the home team or the away team.")

        # Strict validation: Player must belong to the batch team
        if self.player:
            if self.player.competing_batch != self.team.batch_code:
                raise ValidationError(
                    f"Player {self.player.full_name} ({self.player.get_competing_batch_display()}) "
                    f"cannot be recorded for {self.team.name}."
                )

    def __str__(self):
        min_display = f"{self.minute}'" if not self.extra_minute else f"{self.minute}+{self.extra_minute}'"
        player_name = self.player.full_name if self.player else "Team"
        return f"[{min_display}] {self.get_event_type_display()} - {player_name} ({self.team.name})"


class AuditLog(models.Model):
    ACTION_CHOICES = [
        ('CREATE', 'Created Object'),
        ('UPDATE', 'Updated Object'),
        ('DELETE', 'Deleted Object'),
        ('PUBLISH', 'Published Match Result'),
        ('CORRECT', 'Corrected Published Match Result'),
        ('APPROVE_PLAYER', 'Approved Player Roster Registration'),
        ('REJECT_PLAYER', 'Rejected Player Roster Registration'),
        ('SUSPEND_MEMBER', 'Suspended Member Account'),
        ('REACTIVATE_MEMBER', 'Reactivated Member Account'),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='audit_actions'
    )
    action_type = models.CharField(max_length=30, choices=ACTION_CHOICES)
    model_name = models.CharField(max_length=100)
    object_id = models.CharField(max_length=100)
    object_repr = models.CharField(max_length=255)
    changes = models.JSONField(default=dict, blank=True)
    notes = models.TextField(blank=True, default='')
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Audit Log'
        verbose_name_plural = 'Audit Logs'

    def __str__(self):
        user_display = self.user.username if self.user else "System"
        return f"{self.timestamp.strftime('%Y-%m-%d %H:%M')} | {user_display} | {self.get_action_type_display()} on {self.model_name} #{self.object_id}"

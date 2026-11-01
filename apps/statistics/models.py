from django.db import models
from apps.competitions.models import Season, BatchTeam
from apps.members.models import MemberProfile


class TournamentAward(models.Model):
    AWARD_CATEGORIES = [
        ('GOLDEN_BOOT', 'Golden Boot (Top Scorer)'),
        ('PLAYMAKER', 'Playmaker of the Tournament (Most Assists)'),
        ('GOLDEN_GLOVE', 'Golden Glove (Clean Sheet Leader)'),
        ('PLAYER_OF_TOURNAMENT', 'Player of the Tournament'),
        ('FAIR_PLAY', 'Fair Play Award'),
        ('FELLOWSHIP_SPIRIT', 'Fellowship in Christ Spirit Award'),
    ]

    season = models.ForeignKey(Season, on_delete=models.CASCADE, related_name='awards')
    category = models.CharField(max_length=30, choices=AWARD_CATEGORIES)
    title = models.CharField(max_length=150)
    recipient_member = models.ForeignKey(
        MemberProfile,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_awards'
    )
    recipient_team = models.ForeignKey(
        BatchTeam,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='received_team_awards'
    )
    citation = models.TextField(
        help_text="Reason for the award, celebrating sportsmanship, excellence, or fellowship spirit"
    )
    awarded_date = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ['season', 'category']
        verbose_name = 'Tournament Award'
        verbose_name_plural = 'Tournament Awards'

    def __str__(self):
        recipient = self.recipient_member.full_name if self.recipient_member else (self.recipient_team.name if self.recipient_team else "Unassigned")
        return f"{self.title} - {recipient} ({self.season.name})"

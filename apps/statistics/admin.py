from django.contrib import admin
from apps.statistics.models import TournamentAward


@admin.register(TournamentAward)
class TournamentAwardAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'season', 'recipient_member', 'recipient_team', 'awarded_date')
    list_filter = ('category', 'season', 'awarded_date')
    search_fields = ('title', 'citation', 'recipient_member__first_name', 'recipient_team__name')

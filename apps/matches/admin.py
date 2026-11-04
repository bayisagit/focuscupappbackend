from django.contrib import admin
from apps.matches.models import Match, MatchSquad, MatchEvent, AuditLog, MatchGraphic


class MatchSquadInline(admin.TabularInline):
    model = MatchSquad
    extra = 1
    autocomplete_fields = ['player']


class MatchEventInline(admin.TabularInline):
    model = MatchEvent
    extra = 1


@admin.register(Match)
class MatchAdmin(admin.ModelAdmin):
    list_display = (
        '__str__', 'round_number', 'match_date', 'kick_off_time',
        'venue', 'status', 'home_score', 'away_score', 'is_published'
    )
    list_filter = ('status', 'is_published', 'season', 'match_date')
    search_fields = ('home_team__name', 'away_team__name', 'venue', 'match_report')
    inlines = [MatchEventInline, MatchSquadInline]
    readonly_fields = ('created_at', 'updated_at')


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('timestamp', 'user', 'action_type', 'model_name', 'object_repr')
    list_filter = ('action_type', 'model_name', 'timestamp')
    search_fields = ('object_repr', 'notes', 'user__username')
    readonly_fields = ('user', 'action_type', 'model_name', 'object_id', 'object_repr', 'changes', 'notes', 'timestamp')

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


@admin.register(MatchGraphic)
class MatchGraphicAdmin(admin.ModelAdmin):
    list_display = ('title', 'graphic_type', 'team', 'opponent_team', 'round_number', 'created_at', 'published_by')
    list_filter = ('graphic_type', 'round_number', 'team', 'created_at')
    search_fields = ('title', 'team__name', 'opponent_team__name', 'match__home_team__name', 'match__away_team__name')
    readonly_fields = ('created_at',)

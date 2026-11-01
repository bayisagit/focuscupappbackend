from django.contrib import admin
from apps.competitions.models import Season, BatchTeam, SeasonTeam


class SeasonTeamInline(admin.TabularInline):
    model = SeasonTeam
    extra = 1


@admin.register(Season)
class SeasonAdmin(admin.ModelAdmin):
    list_display = ('name', 'academic_year', 'semester', 'status', 'is_active', 'start_date', 'end_date')
    list_filter = ('status', 'is_active', 'academic_year', 'semester')
    search_fields = ('name', 'academic_year')
    inlines = [SeasonTeamInline]


@admin.register(BatchTeam)
class BatchTeamAdmin(admin.ModelAdmin):
    list_display = ('name', 'batch_code', 'nickname', 'color_hex', 'is_competing', 'created_at')
    list_filter = ('is_competing', 'batch_code')
    search_fields = ('name', 'nickname', 'motto')

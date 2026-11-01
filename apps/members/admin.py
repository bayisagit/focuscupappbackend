from django.contrib import admin
from apps.members.models import MemberProfile, MemberFollow, PlayerRegistration


@admin.register(MemberProfile)
class MemberProfileAdmin(admin.ModelAdmin):
    list_display = (
        'full_name', 'college', 'department', 'academic_year',
        'competing_batch', 'fellowship_team', 'gender',
        'primary_position', 'is_football_eligible', 'followers_count',
        'is_approved', 'is_suspended'
    )
    list_filter = (
        'college', 'academic_year', 'competing_batch',
        'fellowship_team', 'gender', 'primary_position',
        'is_football_eligible', 'is_approved', 'is_suspended'
    )
    search_fields = ('first_name', 'second_name', 'user__username', 'user__email', 'department', 'personal_chant')
    readonly_fields = ('followers_count', 'following_count', 'is_football_eligible', 'competing_batch', 'created_at', 'updated_at')
    fieldsets = (
        ('Account & Identity', {'fields': ('user', 'first_name', 'second_name', 'gender', 'profile_picture')}),
        ('Academic Affiliation', {'fields': ('college', 'department', 'academic_year', 'is_football_eligible', 'competing_batch')}),
        ('Fellowship Community', {'fields': ('fellowship_team', 'personal_chant', 'bio', 'followers_count', 'following_count')}),
        ('Football Attributes', {'fields': ('primary_position', 'secondary_position', 'preferred_jersey_number', 'jersey_picture')}),
        ('Moderation', {'fields': ('is_approved', 'is_suspended')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


@admin.register(MemberFollow)
class MemberFollowAdmin(admin.ModelAdmin):
    list_display = ('follower', 'following', 'created_at')
    search_fields = ('follower__username', 'following__username')
    date_hierarchy = 'created_at'


@admin.register(PlayerRegistration)
class PlayerRegistrationAdmin(admin.ModelAdmin):
    list_display = (
        'member', 'batch_team', 'season', 'jersey_number',
        'preferred_position', 'status', 'reviewed_by', 'reviewed_at', 'created_at'
    )
    list_filter = ('status', 'batch_team', 'season', 'preferred_position')
    search_fields = ('member__first_name', 'member__second_name', 'jersey_number', 'football_notes')
    readonly_fields = ('created_at', 'updated_at')

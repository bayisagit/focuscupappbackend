from rest_framework import serializers
from apps.competitions.models import Season, BatchTeam, SeasonTeam
from apps.members.models import MemberProfile, PlayerRegistration


class BatchTeamSerializer(serializers.ModelSerializer):
    total_members = serializers.SerializerMethodField()
    approved_players = serializers.SerializerMethodField()

    class Meta:
        model = BatchTeam
        fields = [
            'id', 'batch_code', 'name', 'nickname', 'color_hex',
            'logo', 'team_photo', 'motto', 'description',
            'is_competing', 'total_members', 'approved_players', 'created_at'
        ]

    def get_total_members(self, obj):
        if obj.batch_code == 'OTHER':
            return MemberProfile.objects.filter(academic_year='Other', is_approved=True).count()
        return MemberProfile.objects.filter(competing_batch=obj.batch_code, is_approved=True).count()

    def get_approved_players(self, obj):
        return PlayerRegistration.objects.filter(batch_team=obj, status='APPROVED').count()


class SeasonSerializer(serializers.ModelSerializer):
    competing_teams_count = serializers.SerializerMethodField()

    class Meta:
        model = Season
        fields = [
            'id', 'name', 'academic_year', 'semester', 'start_date',
            'end_date', 'registration_start', 'registration_end',
            'status', 'is_active', 'rules', 'competing_teams_count', 'created_at'
        ]

    def get_competing_teams_count(self, obj):
        return BatchTeam.objects.filter(is_competing=True).count()

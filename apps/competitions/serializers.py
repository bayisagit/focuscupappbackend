from rest_framework import serializers
from apps.competitions.models import Season, BatchTeam, SeasonTeam
from apps.members.models import MemberProfile, PlayerRegistration


class BatchTeamSerializer(serializers.ModelSerializer):
    total_members = serializers.SerializerMethodField()
    approved_players = serializers.SerializerMethodField()
    photo_url = serializers.CharField(read_only=True, allow_null=True)
    logo_url = serializers.CharField(read_only=True, allow_null=True)
    team_photo_url = serializers.CharField(read_only=True, allow_null=True)
    coach_name = serializers.CharField(source='coach_member.full_name', read_only=True, allow_null=True)
    coach_photo_url = serializers.CharField(source='coach_member.avatar_url', read_only=True, allow_null=True)
    coach_member_id = serializers.IntegerField(source='coach_member.id', read_only=True, allow_null=True)

    class Meta:
        model = BatchTeam
        fields = [
            'id', 'batch_code', 'name', 'nickname', 'color_hex',
            'logo', 'logo_url', 'team_photo', 'team_photo_url', 'photo_url',
            'motto', 'description', 'coach_name', 'coach_photo_url', 'coach_member_id',
            'is_competing', 'total_members', 'approved_players', 'created_at'
        ]

    def get_total_members(self, obj):
        try:
            if obj.batch_code == 'OTHER':
                return MemberProfile.objects.filter(academic_year='Other', is_approved=True).count()
            return MemberProfile.objects.filter(competing_batch=obj.batch_code, is_approved=True).count()
        except Exception:
            return 0

    def get_approved_players(self, obj):
        try:
            return PlayerRegistration.objects.filter(batch_team=obj, status='APPROVED').count()
        except Exception:
            return 0


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

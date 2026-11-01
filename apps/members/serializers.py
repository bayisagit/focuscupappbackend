from rest_framework import serializers
from django.contrib.auth import get_user_model
from apps.members.models import MemberProfile, MemberFollow, PlayerRegistration
from apps.matches.models import MatchSquad, MatchEvent
from apps.statistics.models import TournamentAward

User = get_user_model()


class MemberProfileListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    college_display = serializers.CharField(source='get_college_display', read_only=True)
    batch_display = serializers.CharField(source='get_competing_batch_display', read_only=True)
    is_following = serializers.SerializerMethodField()

    class Meta:
        model = MemberProfile
        fields = [
            'id', 'username', 'first_name', 'second_name', 'full_name',
            'college', 'college_display', 'department', 'academic_year',
            'batch_display', 'competing_batch', 'fellowship_team', 'gender',
            'primary_position', 'preferred_jersey_number', 'profile_picture',
            'personal_chant', 'followers_count', 'following_count',
            'is_football_eligible', 'is_following', 'created_at'
        ]

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return MemberFollow.objects.filter(follower=request.user, following=obj.user).exists()
        return False


class MemberProfileDetailSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    college_display = serializers.CharField(source='get_college_display', read_only=True)
    batch_display = serializers.CharField(source='get_competing_batch_display', read_only=True)
    is_following = serializers.SerializerMethodField()
    football_stats = serializers.SerializerMethodField()
    player_registration = serializers.SerializerMethodField()
    awards = serializers.SerializerMethodField()

    class Meta:
        model = MemberProfile
        fields = [
            'id', 'username', 'first_name', 'second_name', 'full_name',
            'college', 'college_display', 'department', 'academic_year',
            'batch_display', 'competing_batch', 'fellowship_team', 'gender',
            'primary_position', 'secondary_position', 'preferred_jersey_number',
            'profile_picture', 'jersey_picture', 'bio', 'personal_chant',
            'followers_count', 'following_count', 'is_football_eligible',
            'is_following', 'football_stats', 'player_registration',
            'awards', 'created_at'
        ]

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return MemberFollow.objects.filter(follower=request.user, following=obj.user).exists()
        return False

    def get_football_stats(self, obj):
        appearances = MatchSquad.objects.filter(
            player=obj,
            match__status='COMPLETED',
            match__is_published=True
        ).count()
        goals = MatchEvent.objects.filter(
            player=obj,
            event_type='GOAL',
            match__status='COMPLETED',
            match__is_published=True
        ).count()
        assists = MatchEvent.objects.filter(
            player=obj,
            event_type='ASSIST',
            match__status='COMPLETED',
            match__is_published=True
        ).count() + MatchEvent.objects.filter(
            related_player=obj,
            event_type='GOAL',
            match__status='COMPLETED',
            match__is_published=True
        ).count()
        potm = obj.potm_awards.filter(status='COMPLETED', is_published=True).count()
        yellows = MatchEvent.objects.filter(
            player=obj,
            event_type='YELLOW_CARD',
            match__status='COMPLETED',
            match__is_published=True
        ).count()
        reds = MatchEvent.objects.filter(
            player=obj,
            event_type='RED_CARD',
            match__status='COMPLETED',
            match__is_published=True
        ).count()

        return {
            'appearances': appearances,
            'goals': goals,
            'assists': assists,
            'player_of_the_match': potm,
            'yellow_cards': yellows,
            'red_cards': reds,
        }

    def get_player_registration(self, obj):
        reg = obj.player_registrations.filter(status='APPROVED').order_by('-created_at').first()
        if reg:
            return {
                'id': reg.id,
                'season_name': reg.season.name,
                'batch_name': reg.batch_team.name,
                'jersey_number': reg.jersey_number,
                'preferred_position': reg.preferred_position,
                'status': reg.status,
            }
        return None

    def get_awards(self, obj):
        awards = TournamentAward.objects.filter(recipient_member=obj).select_related('season')
        return [
            {
                'id': a.id,
                'category': a.get_category_display(),
                'title': a.title,
                'citation': a.citation,
                'season_name': a.season.name,
                'awarded_date': a.awarded_date,
            } for a in awards
        ]


class MemberProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberProfile
        fields = [
            'first_name', 'second_name', 'fellowship_team', 'primary_position',
            'secondary_position', 'preferred_jersey_number',
            'profile_picture', 'jersey_picture', 'bio', 'personal_chant'
        ]


class PlayerRegistrationSerializer(serializers.ModelSerializer):
    member_name = serializers.CharField(source='member.full_name', read_only=True)
    season_name = serializers.CharField(source='season.name', read_only=True)
    batch_name = serializers.CharField(source='batch_team.name', read_only=True)

    class Meta:
        model = PlayerRegistration
        fields = [
            'id', 'member', 'member_name', 'season', 'season_name',
            'batch_team', 'batch_name', 'preferred_position',
            'jersey_number', 'jersey_photo', 'football_notes',
            'status', 'reviewed_at', 'rejection_reason', 'created_at'
        ]
        read_only_fields = ['status', 'reviewed_by', 'reviewed_at', 'rejection_reason', 'created_at']

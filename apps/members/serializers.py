from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
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
        # 1. Appearances
        squad_qs = (
            MatchSquad.objects.filter(
                player=obj,
                match__status='COMPLETED',
                match__is_published=True
            )
            .select_related('match', 'match__home_team', 'match__away_team', 'team')
            .order_by('-match__match_date', '-match__kick_off_time')
        )
        appearances_list = []
        for sq in squad_qs:
            m = sq.match
            is_home = sq.team_id == m.home_team_id
            opp = m.away_team if is_home else m.home_team
            appearances_list.append({
                'id': sq.id,
                'match_id': m.id,
                'match_date': str(m.match_date),
                'venue': m.venue,
                'stage': f"Round {m.round_number}",
                'round_number': m.round_number,
                'team_represented': sq.team.name,
                'team_represented_code': sq.team.batch_code,
                'opponent_team': opp.name,
                'opponent_nickname': opp.nickname,
                'opponent_batch_code': opp.batch_code,
                'jersey_number': sq.jersey_number,
                'is_starter': sq.is_starter,
                'role': 'Starter' if sq.is_starter else 'Substitute',
                'home_team_name': m.home_team.name,
                'away_team_name': m.away_team.name,
                'home_score': m.home_score,
                'away_score': m.away_score,
                'scoreline': f"{m.home_team.name} {m.home_score} - {m.away_score} {m.away_team.name}",
            })

        # 2. Goals
        goals_qs = (
            MatchEvent.objects.filter(
                player=obj,
                event_type='GOAL',
                match__status='COMPLETED',
                match__is_published=True
            )
            .select_related('match', 'match__home_team', 'match__away_team', 'team', 'related_player')
            .order_by('-match__match_date', 'minute')
        )
        goals_list = []
        for ev in goals_qs:
            m = ev.match
            is_home = ev.team_id == m.home_team_id
            opp = m.away_team if is_home else m.home_team
            goals_list.append({
                'id': ev.id,
                'match_id': m.id,
                'match_date': str(m.match_date),
                'venue': m.venue,
                'stage': f"Round {m.round_number}",
                'round_number': m.round_number,
                'minute': ev.minute,
                'extra_minute': ev.extra_minute,
                'team_represented': ev.team.name,
                'opponent_team': opp.name,
                'opponent_nickname': opp.nickname,
                'opponent_batch_code': opp.batch_code,
                'home_team_name': m.home_team.name,
                'away_team_name': m.away_team.name,
                'home_score': m.home_score,
                'away_score': m.away_score,
                'scoreline': f"{m.home_team.name} {m.home_score} - {m.away_score} {m.away_team.name}",
                'assister_name': ev.related_player.full_name if ev.related_player else None,
                'description': ev.description or 'Goal scored',
            })

        # 3. Assists
        assists_ev_qs = (
            MatchEvent.objects.filter(
                Q(event_type='ASSIST', player=obj) | Q(event_type='GOAL', related_player=obj),
                match__status='COMPLETED',
                match__is_published=True
            )
            .select_related('match', 'match__home_team', 'match__away_team', 'team', 'player', 'related_player')
            .order_by('-match__match_date', 'minute')
        )
        assists_list = []
        for ev in assists_ev_qs:
            m = ev.match
            is_home = ev.team_id == m.home_team_id
            opp = m.away_team if is_home else m.home_team
            scorer_name = ev.player.full_name if ev.player and ev.player != obj else 'Team Goal'
            assists_list.append({
                'id': ev.id,
                'match_id': m.id,
                'match_date': str(m.match_date),
                'venue': m.venue,
                'stage': f"Round {m.round_number}",
                'round_number': m.round_number,
                'minute': ev.minute,
                'extra_minute': ev.extra_minute,
                'team_represented': ev.team.name,
                'opponent_team': opp.name,
                'opponent_nickname': opp.nickname,
                'opponent_batch_code': opp.batch_code,
                'home_team_name': m.home_team.name,
                'away_team_name': m.away_team.name,
                'home_score': m.home_score,
                'away_score': m.away_score,
                'scoreline': f"{m.home_team.name} {m.home_score} - {m.away_score} {m.away_team.name}",
                'scorer_name': scorer_name,
                'description': ev.description or 'Assisted teammate goal',
            })

        # 4. POTM Awards
        potm_matches = (
            obj.potm_awards.filter(
                status='COMPLETED',
                is_published=True
            )
            .select_related('home_team', 'away_team')
            .order_by('-match_date')
        )
        potm_list = []
        for m in potm_matches:
            is_home = obj.competing_batch == m.home_team.batch_code
            opp = m.away_team if is_home else m.home_team
            team_rep = m.home_team if is_home else m.away_team
            potm_list.append({
                'id': m.id,
                'match_id': m.id,
                'match_date': str(m.match_date),
                'venue': m.venue,
                'stage': f"Round {m.round_number}",
                'round_number': m.round_number,
                'team_represented': team_rep.name,
                'opponent_team': opp.name,
                'opponent_nickname': opp.nickname,
                'opponent_batch_code': opp.batch_code,
                'home_team_name': m.home_team.name,
                'away_team_name': m.away_team.name,
                'home_score': m.home_score,
                'away_score': m.away_score,
                'scoreline': f"{m.home_team.name} {m.home_score} - {m.away_score} {m.away_team.name}",
                'citation': 'Official Match MVP – Recognized for outstanding football excellence and fellowship character',
            })

        # 5. Yellow Cards
        yellows_qs = (
            MatchEvent.objects.filter(
                player=obj,
                event_type='YELLOW_CARD',
                match__status='COMPLETED',
                match__is_published=True
            )
            .select_related('match', 'match__home_team', 'match__away_team', 'team')
            .order_by('-match__match_date', 'minute')
        )
        yellows_list = []
        for ev in yellows_qs:
            m = ev.match
            is_home = ev.team_id == m.home_team_id
            opp = m.away_team if is_home else m.home_team
            yellows_list.append({
                'id': ev.id,
                'match_id': m.id,
                'match_date': str(m.match_date),
                'venue': m.venue,
                'stage': f"Round {m.round_number}",
                'round_number': m.round_number,
                'minute': ev.minute,
                'team_represented': ev.team.name,
                'opponent_team': opp.name,
                'opponent_nickname': opp.nickname,
                'opponent_batch_code': opp.batch_code,
                'home_team_name': m.home_team.name,
                'away_team_name': m.away_team.name,
                'home_score': m.home_score,
                'away_score': m.away_score,
                'scoreline': f"{m.home_team.name} {m.home_score} - {m.away_score} {m.away_team.name}",
                'description': ev.description or 'Cautioned by referee',
            })

        # 6. Red Cards
        reds_qs = (
            MatchEvent.objects.filter(
                player=obj,
                event_type='RED_CARD',
                match__status='COMPLETED',
                match__is_published=True
            )
            .select_related('match', 'match__home_team', 'match__away_team', 'team')
            .order_by('-match__match_date', 'minute')
        )
        reds_list = []
        for ev in reds_qs:
            m = ev.match
            is_home = ev.team_id == m.home_team_id
            opp = m.away_team if is_home else m.home_team
            reds_list.append({
                'id': ev.id,
                'match_id': m.id,
                'match_date': str(m.match_date),
                'venue': m.venue,
                'stage': f"Round {m.round_number}",
                'round_number': m.round_number,
                'minute': ev.minute,
                'team_represented': ev.team.name,
                'opponent_team': opp.name,
                'opponent_nickname': opp.nickname,
                'opponent_batch_code': opp.batch_code,
                'home_team_name': m.home_team.name,
                'away_team_name': m.away_team.name,
                'home_score': m.home_score,
                'away_score': m.away_score,
                'scoreline': f"{m.home_team.name} {m.home_score} - {m.away_score} {m.away_team.name}",
                'description': ev.description or 'Dismissed by referee',
            })

        return {
            'appearances': len(appearances_list),
            'goals': len(goals_list),
            'assists': len(assists_list),
            'player_of_the_match': len(potm_list),
            'yellow_cards': len(yellows_list),
            'red_cards': len(reds_list),
            'appearances_list': appearances_list,
            'goals_list': goals_list,
            'assists_list': assists_list,
            'potm_list': potm_list,
            'yellow_cards_list': yellows_list,
            'red_cards_list': reds_list,
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

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.db.models import Q
from apps.members.models import MemberProfile, MemberFollow, PlayerRegistration
from apps.members.constants import validate_academic_eligibility
from apps.matches.models import MatchSquad, MatchEvent
from apps.statistics.models import TournamentAward

User = get_user_model()


class MemberProfileListSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    college_display = serializers.CharField(source='get_college_display', read_only=True)
    batch_display = serializers.CharField(source='get_competing_batch_display', read_only=True)
    is_following = serializers.SerializerMethodField()
    profile_picture = serializers.SerializerMethodField()
    is_coach = serializers.BooleanField(read_only=True)
    coached_batch_name = serializers.CharField(read_only=True)
    coached_batch_code = serializers.CharField(read_only=True)

    class Meta:
        model = MemberProfile
        fields = [
            'id', 'username', 'first_name', 'second_name', 'full_name',
            'college', 'college_display', 'department', 'academic_year',
            'batch_display', 'competing_batch', 'fellowship_team', 'gender',
            'primary_position', 'preferred_jersey_number', 'profile_picture',
            'profile_picture_url', 'personal_chant', 'followers_count', 'following_count',
            'is_football_eligible', 'is_following', 'is_coach', 'coached_batch_name',
            'coached_batch_code', 'created_at'
        ]

    def get_profile_picture(self, obj):
        return obj.avatar_url

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
    profile_picture = serializers.SerializerMethodField()
    football_stats = serializers.SerializerMethodField()
    player_registration = serializers.SerializerMethodField()
    awards = serializers.SerializerMethodField()
    is_coach = serializers.BooleanField(read_only=True)
    coached_batch_name = serializers.CharField(read_only=True)
    coached_batch_code = serializers.CharField(read_only=True)

    class Meta:
        model = MemberProfile
        fields = [
            'id', 'username', 'first_name', 'second_name', 'full_name',
            'college', 'college_display', 'department', 'academic_year',
            'batch_display', 'competing_batch', 'fellowship_team', 'gender',
            'primary_position', 'secondary_position', 'preferred_jersey_number',
            'profile_picture', 'profile_picture_url', 'jersey_picture', 'bio', 'personal_chant',
            'followers_count', 'following_count', 'is_football_eligible',
            'is_following', 'is_coach', 'coached_batch_name', 'coached_batch_code',
            'football_stats', 'player_registration',
            'awards', 'created_at'
        ]

    def get_profile_picture(self, obj):
        return obj.avatar_url

    def get_is_following(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return MemberFollow.objects.filter(follower=request.user, following=obj.user).exists()
        return False

    def get_football_stats(self, obj):
        try:
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
                if not m:
                    continue
                is_home = sq.team_id == m.home_team_id
                opp = m.away_team if is_home else m.home_team
                team_name = sq.team.name if sq.team else (m.home_team.name if is_home and m.home_team else (m.away_team.name if m.away_team else ''))
                team_code = sq.team.batch_code if sq.team else ''
                opp_name = opp.name if opp else ''
                opp_nick = opp.nickname if opp else ''
                opp_code = opp.batch_code if opp else ''
                home_name = m.home_team.name if m.home_team else ''
                away_name = m.away_team.name if m.away_team else ''
                appearances_list.append({
                    'id': sq.id,
                    'match_id': m.id,
                    'match_date': str(m.match_date) if m.match_date else '',
                    'venue': m.venue or '',
                    'stage': f"Round {m.round_number}",
                    'round_number': m.round_number,
                    'team_represented': team_name,
                    'team_represented_code': team_code,
                    'opponent_team': opp_name,
                    'opponent_nickname': opp_nick,
                    'opponent_batch_code': opp_code,
                    'jersey_number': sq.jersey_number,
                    'is_starter': sq.is_starter,
                    'role': 'Starter' if sq.is_starter else 'Substitute',
                    'home_team_name': home_name,
                    'away_team_name': away_name,
                    'home_score': m.home_score,
                    'away_score': m.away_score,
                    'scoreline': f"{home_name} {m.home_score} - {m.away_score} {away_name}",
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
                if not m:
                    continue
                is_home = ev.team_id == m.home_team_id
                opp = m.away_team if is_home else m.home_team
                team_name = ev.team.name if ev.team else ''
                opp_name = opp.name if opp else ''
                opp_nick = opp.nickname if opp else ''
                opp_code = opp.batch_code if opp else ''
                home_name = m.home_team.name if m.home_team else ''
                away_name = m.away_team.name if m.away_team else ''
                goals_list.append({
                    'id': ev.id,
                    'match_id': m.id,
                    'match_date': str(m.match_date) if m.match_date else '',
                    'venue': m.venue or '',
                    'stage': f"Round {m.round_number}",
                    'round_number': m.round_number,
                    'minute': ev.minute,
                    'extra_minute': ev.extra_minute,
                    'team_represented': team_name,
                    'opponent_team': opp_name,
                    'opponent_nickname': opp_nick,
                    'opponent_batch_code': opp_code,
                    'home_team_name': home_name,
                    'away_team_name': away_name,
                    'home_score': m.home_score,
                    'away_score': m.away_score,
                    'scoreline': f"{home_name} {m.home_score} - {m.away_score} {away_name}",
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
                if not m:
                    continue
                is_home = ev.team_id == m.home_team_id
                opp = m.away_team if is_home else m.home_team
                scorer_name = ev.player.full_name if ev.player and ev.player != obj else 'Team Goal'
                team_name = ev.team.name if ev.team else ''
                opp_name = opp.name if opp else ''
                opp_nick = opp.nickname if opp else ''
                opp_code = opp.batch_code if opp else ''
                home_name = m.home_team.name if m.home_team else ''
                away_name = m.away_team.name if m.away_team else ''
                assists_list.append({
                    'id': ev.id,
                    'match_id': m.id,
                    'match_date': str(m.match_date) if m.match_date else '',
                    'venue': m.venue or '',
                    'stage': f"Round {m.round_number}",
                    'round_number': m.round_number,
                    'minute': ev.minute,
                    'extra_minute': ev.extra_minute,
                    'team_represented': team_name,
                    'opponent_team': opp_name,
                    'opponent_nickname': opp_nick,
                    'opponent_batch_code': opp_code,
                    'home_team_name': home_name,
                    'away_team_name': away_name,
                    'home_score': m.home_score,
                    'away_score': m.away_score,
                    'scoreline': f"{home_name} {m.home_score} - {m.away_score} {away_name}",
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
                home_batch = m.home_team.batch_code if m.home_team else ''
                is_home = obj.competing_batch == home_batch
                opp = m.away_team if is_home else m.home_team
                team_rep = m.home_team if is_home else m.away_team
                team_rep_name = team_rep.name if team_rep else ''
                opp_name = opp.name if opp else ''
                opp_nick = opp.nickname if opp else ''
                opp_code = opp.batch_code if opp else ''
                home_name = m.home_team.name if m.home_team else ''
                away_name = m.away_team.name if m.away_team else ''
                potm_list.append({
                    'id': m.id,
                    'match_id': m.id,
                    'match_date': str(m.match_date) if m.match_date else '',
                    'venue': m.venue or '',
                    'stage': f"Round {m.round_number}",
                    'round_number': m.round_number,
                    'team_represented': team_rep_name,
                    'opponent_team': opp_name,
                    'opponent_nickname': opp_nick,
                    'opponent_batch_code': opp_code,
                    'home_team_name': home_name,
                    'away_team_name': away_name,
                    'home_score': m.home_score,
                    'away_score': m.away_score,
                    'scoreline': f"{home_name} {m.home_score} - {m.away_score} {away_name}",
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
                if not m:
                    continue
                is_home = ev.team_id == m.home_team_id
                opp = m.away_team if is_home else m.home_team
                team_name = ev.team.name if ev.team else ''
                opp_name = opp.name if opp else ''
                opp_nick = opp.nickname if opp else ''
                opp_code = opp.batch_code if opp else ''
                home_name = m.home_team.name if m.home_team else ''
                away_name = m.away_team.name if m.away_team else ''
                yellows_list.append({
                    'id': ev.id,
                    'match_id': m.id,
                    'match_date': str(m.match_date) if m.match_date else '',
                    'venue': m.venue or '',
                    'stage': f"Round {m.round_number}",
                    'round_number': m.round_number,
                    'minute': ev.minute,
                    'team_represented': team_name,
                    'opponent_team': opp_name,
                    'opponent_nickname': opp_nick,
                    'opponent_batch_code': opp_code,
                    'home_team_name': home_name,
                    'away_team_name': away_name,
                    'home_score': m.home_score,
                    'away_score': m.away_score,
                    'scoreline': f"{home_name} {m.home_score} - {m.away_score} {away_name}",
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
                if not m:
                    continue
                is_home = ev.team_id == m.home_team_id
                opp = m.away_team if is_home else m.home_team
                team_name = ev.team.name if ev.team else ''
                opp_name = opp.name if opp else ''
                opp_nick = opp.nickname if opp else ''
                opp_code = opp.batch_code if opp else ''
                home_name = m.home_team.name if m.home_team else ''
                away_name = m.away_team.name if m.away_team else ''
                reds_list.append({
                    'id': ev.id,
                    'match_id': m.id,
                    'match_date': str(m.match_date) if m.match_date else '',
                    'venue': m.venue or '',
                    'stage': f"Round {m.round_number}",
                    'round_number': m.round_number,
                    'minute': ev.minute,
                    'team_represented': team_name,
                    'opponent_team': opp_name,
                    'opponent_nickname': opp_nick,
                    'opponent_batch_code': opp_code,
                    'home_team_name': home_name,
                    'away_team_name': away_name,
                    'home_score': m.home_score,
                    'away_score': m.away_score,
                    'scoreline': f"{home_name} {m.home_score} - {m.away_score} {away_name}",
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
        except Exception:
            return {
                'appearances': 0,
                'goals': 0,
                'assists': 0,
                'player_of_the_match': 0,
                'yellow_cards': 0,
                'red_cards': 0,
                'appearances_list': [],
                'goals_list': [],
                'assists_list': [],
                'potm_list': [],
                'yellow_cards_list': [],
                'red_cards_list': [],
            }

    def get_player_registration(self, obj):
        try:
            reg = obj.player_registrations.filter(status='APPROVED').select_related('season', 'batch_team').order_by('-created_at').first()
            if reg:
                return {
                    'id': reg.id,
                    'season_name': reg.season.name if reg.season else '',
                    'batch_name': reg.batch_team.name if reg.batch_team else '',
                    'jersey_number': reg.jersey_number,
                    'preferred_position': reg.preferred_position,
                    'status': reg.status,
                }
        except Exception:
            pass
        return None

    def get_awards(self, obj):
        try:
            awards = TournamentAward.objects.filter(recipient_member=obj).select_related('season')
            return [
                {
                    'id': a.id,
                    'category': a.get_category_display() if hasattr(a, 'get_category_display') else str(a.category),
                    'title': a.title,
                    'citation': a.citation,
                    'season_name': a.season.name if a.season else '',
                    'awarded_date': a.awarded_date,
                } for a in awards
            ]
        except Exception:
            return []


class MemberProfileUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = MemberProfile
        fields = [
            'first_name', 'second_name', 'college', 'department', 'academic_year',
            'fellowship_team', 'gender', 'primary_position',
            'secondary_position', 'preferred_jersey_number',
            'profile_picture', 'profile_picture_url', 'jersey_picture', 'bio', 'personal_chant'
        ]

    def validate(self, attrs):
        college = attrs.get('college', getattr(self.instance, 'college', None))
        department = attrs.get('department', getattr(self.instance, 'department', None))
        academic_year = attrs.get('academic_year', getattr(self.instance, 'academic_year', None))

        if college or department or academic_year:
            is_valid, err_msg, _, _ = validate_academic_eligibility(college, department, academic_year)
            if not is_valid:
                raise serializers.ValidationError({"department": err_msg or "Invalid college, department, or academic year combination."})

        return attrs


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

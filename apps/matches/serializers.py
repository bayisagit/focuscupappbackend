from rest_framework import serializers
from apps.matches.models import Match, MatchSquad, MatchEvent
from apps.competitions.serializers import BatchTeamSerializer


class MatchEventSerializer(serializers.ModelSerializer):
    event_type_display = serializers.CharField(source='get_event_type_display', read_only=True)
    player_name = serializers.CharField(source='player.full_name', read_only=True)
    related_player_name = serializers.CharField(source='related_player.full_name', read_only=True)
    team_name = serializers.CharField(source='team.name', read_only=True)
    team_batch = serializers.CharField(source='team.batch_code', read_only=True)

    class Meta:
        model = MatchEvent
        fields = [
            'id', 'match', 'event_type', 'event_type_display',
            'team', 'team_name', 'team_batch',
            'player', 'player_name',
            'related_player', 'related_player_name',
            'minute', 'extra_minute', 'description', 'created_at'
        ]


class MatchSquadSerializer(serializers.ModelSerializer):
    player_name = serializers.CharField(source='player.full_name', read_only=True)
    player_username = serializers.CharField(source='player.user.username', read_only=True)
    player_photo = serializers.SerializerMethodField()
    position = serializers.CharField(source='player.primary_position', read_only=True)

    class Meta:
        model = MatchSquad
        fields = [
            'id', 'player', 'player_name', 'player_username',
            'player_photo', 'position', 'jersey_number',
            'is_starter', 'is_goalkeeper'
        ]

    def get_player_photo(self, obj):
        return obj.player.avatar_url


class MatchListSerializer(serializers.ModelSerializer):
    home_team = BatchTeamSerializer(read_only=True)
    away_team = BatchTeamSerializer(read_only=True)
    season_name = serializers.SerializerMethodField()
    potm_name = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            'id', 'season', 'season_name', 'round_number',
            'home_team', 'away_team', 'match_date', 'kick_off_time',
            'venue', 'status', 'home_score', 'away_score',
            'is_published', 'potm_name', 'created_at'
        ]

    def get_season_name(self, obj):
        try:
            return obj.season.name if obj.season else None
        except Exception:
            return None

    def get_potm_name(self, obj):
        try:
            return obj.player_of_the_match.full_name if obj.player_of_the_match else None
        except Exception:
            return None


class MatchDetailSerializer(serializers.ModelSerializer):
    home_team = BatchTeamSerializer(read_only=True)
    away_team = BatchTeamSerializer(read_only=True)
    season_name = serializers.SerializerMethodField()
    events = MatchEventSerializer(many=True, read_only=True)
    home_squad = serializers.SerializerMethodField()
    away_squad = serializers.SerializerMethodField()
    player_of_the_match_details = serializers.SerializerMethodField()

    class Meta:
        model = Match
        fields = [
            'id', 'season', 'season_name', 'round_number',
            'home_team', 'away_team', 'match_date', 'kick_off_time',
            'venue', 'status', 'home_score', 'away_score',
            'is_published', 'match_report', 'events',
            'home_squad', 'away_squad',
            'player_of_the_match', 'player_of_the_match_details',
            'created_at', 'updated_at'
        ]

    def get_season_name(self, obj):
        try:
            return obj.season.name if obj.season else None
        except Exception:
            return None

    def get_home_squad(self, obj):
        entries = MatchSquad.objects.filter(match=obj, team=obj.home_team).select_related('player', 'player__user')
        return MatchSquadSerializer(entries, many=True).data

    def get_away_squad(self, obj):
        entries = MatchSquad.objects.filter(match=obj, team=obj.away_team).select_related('player', 'player__user')
        return MatchSquadSerializer(entries, many=True).data

    def get_player_of_the_match_details(self, obj):
        potm = obj.player_of_the_match
        if not potm:
            return None
        return {
            'id': potm.id,
            'username': potm.user.username,
            'full_name': potm.full_name,
            'batch': potm.get_competing_batch_display(),
            'profile_picture': potm.avatar_url,
            'avatar_url': potm.avatar_url,
            'profile_picture_url': potm.profile_picture_url,
            'personal_chant': potm.personal_chant,
        }

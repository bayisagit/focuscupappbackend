from rest_framework import permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.statistics.services import (
    get_top_goalscorers,
    get_top_assists,
    get_most_followed_members,
    get_tournament_summary,
    get_active_season,
)
from apps.statistics.models import TournamentAward


class TopScorersAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        season_id = request.query_params.get('season')
        limit = int(request.query_params.get('limit', 10))
        scorers = get_top_goalscorers(season_id=season_id, limit=limit)
        return Response(scorers)


class TopAssistsAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        season_id = request.query_params.get('season')
        limit = int(request.query_params.get('limit', 10))
        assists = get_top_assists(season_id=season_id, limit=limit)
        return Response(assists)


class MostFollowedMembersAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        batch = request.query_params.get('batch')
        limit = int(request.query_params.get('limit', 10))
        members = get_most_followed_members(limit=limit, batch_code=batch)
        return Response(members)


class TournamentSummaryAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        season_id = request.query_params.get('season')
        summary = get_tournament_summary(season_id=season_id)
        return Response(summary)


class AwardsListAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        season_id = request.query_params.get('season')
        qs = TournamentAward.objects.select_related('recipient_member', 'recipient_team', 'season').all()
        if season_id:
            qs = qs.filter(season_id=season_id)
        else:
            active_season = get_active_season()
            if active_season:
                qs = qs.filter(season=active_season)

        awards = [
            {
                'id': a.id,
                'category': a.get_category_display(),
                'title': a.title,
                'citation': a.citation,
                'recipient_member': {
                    'id': a.recipient_member.id,
                    'full_name': a.recipient_member.full_name,
                    'batch': a.recipient_member.get_competing_batch_display(),
                    'profile_picture': a.recipient_member.profile_picture.url if a.recipient_member.profile_picture else None,
                } if a.recipient_member else None,
                'recipient_team': {
                    'id': a.recipient_team.id,
                    'name': a.recipient_team.name,
                    'batch_code': a.recipient_team.batch_code,
                    'color_hex': a.recipient_team.color_hex,
                } if a.recipient_team else None,
                'season_name': a.season.name,
                'awarded_date': a.awarded_date,
            } for a in qs
        ]
        return Response(awards)

from rest_framework import permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.matches.models import Match
from apps.matches.serializers import MatchListSerializer, MatchDetailSerializer
from apps.statistics.services import get_active_season


class MatchListAPIView(generics.ListAPIView):
    """List fixtures and results with powerful filters."""
    serializer_class = MatchListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Match.objects.select_related('home_team', 'away_team', 'season', 'player_of_the_match').all()

        season_id = self.request.query_params.get('season')
        if season_id:
            qs = qs.filter(season_id=season_id)
        else:
            active_season = get_active_season()
            if active_season:
                qs = qs.filter(season=active_season)

        batch = self.request.query_params.get('batch')
        if batch:
            qs = qs.filter(Q(home_team__batch_code=batch) | Q(away_team__batch_code=batch))

        match_status = self.request.query_params.get('status')
        if match_status:
            qs = qs.filter(status=match_status)

        category = self.request.query_params.get('category')
        if category == 'fixtures':
            # Upcoming or ongoing matches
            qs = qs.filter(status__in=['SCHEDULED', 'LIVE', 'HALF_TIME', 'POSTPONED']).order_by('match_date', 'kick_off_time')
        elif category == 'results':
            # Completed & published results
            qs = qs.filter(status='COMPLETED', is_published=True).order_by('-match_date', '-kick_off_time')
        else:
            qs = qs.order_by('match_date', 'kick_off_time')

        return qs


class MatchDetailAPIView(APIView):
    """Full Match Center data including events, squads, and POTM."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team', 'season', 'player_of_the_match'),
            pk=pk
        )
        serializer = MatchDetailSerializer(match)
        return Response(serializer.data)


class LatestAndNextMatchAPIView(APIView):
    """Provides homepage with latest published match result and next scheduled match."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        season = get_active_season()
        latest_result = None
        next_upcoming = None

        if season:
            latest = (
                Match.objects.filter(season=season, status='COMPLETED', is_published=True)
                .select_related('home_team', 'away_team', 'season')
                .order_by('-match_date', '-kick_off_time')
                .first()
            )
            if latest:
                latest_result = MatchListSerializer(latest).data

            upcoming = (
                Match.objects.filter(season=season, status__in=['SCHEDULED', 'LIVE', 'HALF_TIME'])
                .select_related('home_team', 'away_team', 'season')
                .order_by('match_date', 'kick_off_time')
                .first()
            )
            if upcoming:
                next_upcoming = MatchListSerializer(upcoming).data

        return Response({
            'latest_result': latest_result,
            'next_upcoming': next_upcoming,
        })

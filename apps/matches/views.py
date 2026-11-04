from rest_framework import permissions, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.matches.models import Match, MatchGraphic
from apps.competitions.models import BatchTeam
from apps.matches.serializers import (
    MatchListSerializer,
    MatchDetailSerializer,
    MatchGraphicSerializer,
)
from apps.statistics.services import get_active_season


class MatchListAPIView(generics.ListAPIView):
    """List fixtures and results with powerful filters."""
    serializer_class = MatchListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = Match.objects.select_related('home_team', 'away_team', 'season').all()

        season_id = self.request.query_params.get('season')
        if season_id:
            qs = qs.filter(season_id=season_id)
        else:
            active_season = get_active_season()
            if active_season and qs.filter(season=active_season).exists():
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

    def list(self, request, *args, **kwargs):
        try:
            return super().list(request, *args, **kwargs)
        except Exception as exc:
            import traceback
            import logging
            logger = logging.getLogger(__name__)
            logger.error("MatchListAPIView error: %s", exc, exc_info=True)
            # Safe serialization fallback
            try:
                queryset = self.filter_queryset(self.get_queryset())
                page = self.paginate_queryset(queryset)
                records = page if page is not None else queryset
                safe_results = []
                for m in records:
                    safe_results.append({
                        'id': m.id,
                        'season': m.season_id,
                        'season_name': m.season.name if m.season else 'Focus Football Cup',
                        'round_number': m.round_number,
                        'home_team': {
                            'id': m.home_team.id if m.home_team else None,
                            'batch_code': m.home_team.batch_code if m.home_team else '',
                            'name': m.home_team.name if m.home_team else '',
                            'nickname': getattr(m.home_team, 'nickname', ''),
                            'color_hex': getattr(m.home_team, 'color_hex', '#10B981'),
                            'logo_url': getattr(m.home_team, 'photo_url', None),
                            'photo_url': getattr(m.home_team, 'photo_url', None),
                        } if m.home_team else None,
                        'away_team': {
                            'id': m.away_team.id if m.away_team else None,
                            'batch_code': m.away_team.batch_code if m.away_team else '',
                            'name': m.away_team.name if m.away_team else '',
                            'nickname': getattr(m.away_team, 'nickname', ''),
                            'color_hex': getattr(m.away_team, 'color_hex', '#3B82F6'),
                            'logo_url': getattr(m.away_team, 'photo_url', None),
                            'photo_url': getattr(m.away_team, 'photo_url', None),
                        } if m.away_team else None,
                        'match_date': str(m.match_date),
                        'kick_off_time': str(m.kick_off_time),
                        'venue': m.venue,
                        'status': m.status,
                        'home_score': m.home_score,
                        'away_score': m.away_score,
                        'is_published': m.is_published,
                        'potm_name': m.player_of_the_match.full_name if m.player_of_the_match else None,
                        'created_at': m.created_at.isoformat() if m.created_at else None,
                    })
                if page is not None:
                    return self.get_paginated_response(safe_results)
                return Response(safe_results)
            except Exception as inner_exc:
                return Response({
                    "error": "Failed to load matches",
                    "detail": str(exc),
                    "inner": str(inner_exc)
                }, status=500)


class MatchDetailAPIView(APIView):
    """Full Match Center data including events, squads, and POTM."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, pk):
        try:
            match = get_object_or_404(
                Match.objects.select_related('home_team', 'away_team', 'season', 'player_of_the_match'),
                pk=pk
            )
            serializer = MatchDetailSerializer(match)
            return Response(serializer.data)
        except Exception as exc:
            import logging
            logger = logging.getLogger(__name__)
            logger.error("MatchDetailAPIView error for pk=%s: %s", pk, exc, exc_info=True)
            return Response({"error": "Failed to load match detail", "detail": str(exc)}, status=500)


class LatestAndNextMatchAPIView(APIView):
    """Provides homepage with latest published match result and next scheduled match."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        try:
            season = get_active_season()
            latest_result = None
            next_upcoming = None

            latest_qs = Match.objects.filter(status='COMPLETED', is_published=True)
            if season and latest_qs.filter(season=season).exists():
                latest_qs = latest_qs.filter(season=season)
            latest = latest_qs.select_related('home_team', 'away_team', 'season').order_by('-match_date', '-kick_off_time').first()
            if latest:
                try:
                    latest_result = MatchListSerializer(latest).data
                except Exception:
                    latest_result = {
                        'id': latest.id,
                        'round_number': latest.round_number,
                        'home_team': {'name': latest.home_team.name, 'batch_code': latest.home_team.batch_code} if latest.home_team else None,
                        'away_team': {'name': latest.away_team.name, 'batch_code': latest.away_team.batch_code} if latest.away_team else None,
                        'home_score': latest.home_score,
                        'away_score': latest.away_score,
                        'status': latest.status,
                        'match_date': str(latest.match_date),
                    }

            upcoming_qs = Match.objects.filter(status__in=['SCHEDULED', 'LIVE', 'HALF_TIME'])
            if season and upcoming_qs.filter(season=season).exists():
                upcoming_qs = upcoming_qs.filter(season=season)
            upcoming = upcoming_qs.select_related('home_team', 'away_team', 'season').order_by('match_date', 'kick_off_time').first()
            if upcoming:
                try:
                    next_upcoming = MatchListSerializer(upcoming).data
                except Exception:
                    next_upcoming = {
                        'id': upcoming.id,
                        'round_number': upcoming.round_number,
                        'home_team': {'name': upcoming.home_team.name, 'batch_code': upcoming.home_team.batch_code} if upcoming.home_team else None,
                        'away_team': {'name': upcoming.away_team.name, 'batch_code': upcoming.away_team.batch_code} if upcoming.away_team else None,
                        'home_score': upcoming.home_score,
                        'away_score': upcoming.away_score,
                        'status': upcoming.status,
                        'match_date': str(upcoming.match_date),
                    }

            return Response({
                'latest_result': latest_result,
                'next_upcoming': next_upcoming,
            })
        except Exception:
            return Response({
                'latest_result': None,
                'next_upcoming': None,
            })


class MatchGraphicListCreateAPIView(APIView):
    """
    List and create archived match graphics (Starting Lineup Posters & Broadcast Graphics).
    Allows managers to review historical lineups and broadcast graphics per round/batch.
    """
    def get_permissions(self):
        if self.request.method == 'GET':
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]

    def get(self, request):
        qs = MatchGraphic.objects.select_related('match', 'team', 'opponent_team', 'published_by').all()

        match_id = request.query_params.get('match_id')
        if match_id:
            qs = qs.filter(match_id=match_id)

        batch_code = request.query_params.get('batch_code')
        if batch_code:
            qs = qs.filter(Q(team__batch_code=batch_code) | Q(opponent_team__batch_code=batch_code))

        round_num = request.query_params.get('round')
        if round_num:
            try:
                qs = qs.filter(round_number=int(round_num))
            except (ValueError, TypeError):
                pass

        graphic_type = request.query_params.get('graphic_type')
        if graphic_type:
            qs = qs.filter(graphic_type=graphic_type)

        serializer = MatchGraphicSerializer(qs, many=True)
        return Response(serializer.data)

    def post(self, request):
        if not (request.user.is_staff or getattr(request.user, 'is_manager', False)):
            return Response({"error": "Manager privileges required."}, status=status.HTTP_403_FORBIDDEN)

        match_id = request.data.get('match_id')
        match_obj = get_object_or_404(Match, id=match_id)

        team_id = request.data.get('team_id')
        team_obj = BatchTeam.objects.filter(id=team_id).first() if team_id else None

        opp_id = request.data.get('opponent_team_id')
        opp_obj = BatchTeam.objects.filter(id=opp_id).first() if opp_id else None

        graphic = MatchGraphic.objects.create(
            match=match_obj,
            graphic_type=request.data.get('graphic_type', 'LINEUP_POSTER'),
            team=team_obj,
            opponent_team=opp_obj,
            round_number=int(request.data.get('round_number') or match_obj.round_number or 1),
            title=request.data.get('title') or f"Matchday Graphic - {match_obj}",
            image_url=request.data.get('image_url', ''),
            data_snapshot=request.data.get('data_snapshot', {}),
            published_by=request.user
        )

        serializer = MatchGraphicSerializer(graphic)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class MatchGraphicDetailAPIView(APIView):
    """Retrieve or delete a published match graphic archive."""
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, pk):
        if not (request.user.is_staff or getattr(request.user, 'is_manager', False)):
            return Response({"error": "Manager privileges required."}, status=status.HTTP_403_FORBIDDEN)

        graphic = get_object_or_404(MatchGraphic, pk=pk)
        graphic.delete()
        return Response({"message": "Graphic deleted successfully from archive."}, status=status.HTTP_204_NO_CONTENT)

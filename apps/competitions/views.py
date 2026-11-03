from rest_framework import permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.competitions.models import Season, BatchTeam
from apps.competitions.serializers import SeasonSerializer, BatchTeamSerializer
from apps.statistics.services import calculate_season_standings, get_active_season
from apps.members.models import MemberProfile, PlayerRegistration
from apps.matches.models import Match


class SeasonListAPIView(generics.ListAPIView):
    serializer_class = SeasonSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Season.objects.all().order_by('-start_date')


class ActiveSeasonAPIView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        season = get_active_season()
        if not season:
            return Response({"error": "No season found."}, status=404)
        return Response(SeasonSerializer(season).data)


class SeasonStandingsAPIView(APIView):
    """Calculated standings for a given season or the active season."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, season_id=None):
        standings = calculate_season_standings(season_id)
        season = Season.objects.filter(pk=season_id).first() if season_id else get_active_season()
        return Response({
            'season_id': season.id if season else None,
            'season_name': season.name if season else "Focus Football Cup",
            'standings': standings,
        })


class BatchTeamListAPIView(generics.ListAPIView):
    serializer_class = BatchTeamSerializer
    permission_classes = [permissions.AllowAny]
    queryset = BatchTeam.objects.all().order_by('batch_code')


class BatchTeamDetailAPIView(APIView):
    """Detailed information, roster, fixtures, and results for an academic batch."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, batch_code):
        team = get_object_or_404(BatchTeam, batch_code=batch_code)
        active_season = get_active_season()

        # Approved players roster for this batch
        roster_entries = (
            PlayerRegistration.objects.filter(batch_team=team, status='APPROVED')
            .select_related('member', 'member__user')
            .order_by('jersey_number')
        )
        roster = [
            {
                'id': reg.id,
                'member_id': reg.member.id,
                'username': reg.member.user.username,
                'full_name': reg.member.full_name,
                'department': reg.member.department,
                'jersey_number': reg.jersey_number,
                'position': reg.preferred_position,
                'profile_picture': reg.member.avatar_url,
                'avatar_url': reg.member.avatar_url,
                'profile_picture_url': reg.member.profile_picture_url,
                'personal_chant': reg.member.personal_chant,
            } for reg in roster_entries
        ]

        # All fellowship members in this batch
        if team.batch_code == 'OTHER':
            members_qs = MemberProfile.objects.filter(academic_year='Other', is_approved=True)
        else:
            members_qs = MemberProfile.objects.filter(competing_batch=team.batch_code, is_approved=True)

        total_members = members_qs.count()

        # Fixtures and Results
        fixtures = []
        results = []
        if active_season:
            team_matches = (
                Match.objects.filter(season=active_season)
                .filter(Q(home_team=team) | Q(away_team=team))
                .select_related('home_team', 'away_team')
                .order_by('match_date', 'kick_off_time')
            )
            for m in team_matches:
                match_data = {
                    'id': m.id,
                    'round_number': m.round_number,
                    'home_team': {'id': m.home_team.id, 'name': m.home_team.name, 'batch_code': m.home_team.batch_code},
                    'away_team': {'id': m.away_team.id, 'name': m.away_team.name, 'batch_code': m.away_team.batch_code},
                    'match_date': m.match_date,
                    'kick_off_time': m.kick_off_time.strftime('%H:%M') if m.kick_off_time else '',
                    'venue': m.venue,
                    'status': m.status,
                    'home_score': m.home_score,
                    'away_score': m.away_score,
                    'is_published': m.is_published,
                }
                if m.status == 'COMPLETED' and m.is_published:
                    results.append(match_data)
                else:
                    fixtures.append(match_data)

        # Batch standings summary
        standings = calculate_season_standings(active_season.id if active_season else None)
        team_standing = next((s for s in standings if s['batch_code'] == team.batch_code), None)

        return Response({
            'team': BatchTeamSerializer(team).data,
            'total_members': total_members,
            'roster': roster,
            'standing': team_standing,
            'fixtures': fixtures,
            'results': results,
        })

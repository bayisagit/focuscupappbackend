from rest_framework import permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from apps.core.permissions import IsTournamentManager
from apps.competitions.models import Season, BatchTeam
from apps.competitions.serializers import SeasonSerializer, BatchTeamSerializer
from apps.statistics.services import calculate_season_standings, get_active_season
from apps.members.models import MemberProfile, PlayerRegistration
from apps.matches.models import Match, AuditLog


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
    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT'):
            return [permissions.IsAuthenticated()]
        return [permissions.AllowAny()]

    def patch(self, request, batch_code):
        team = get_object_or_404(BatchTeam, batch_code=batch_code)

        is_mgr = bool(
            request.user.is_authenticated and (
                request.user.role == 'MANAGER' or
                getattr(request.user, 'is_manager', False) or
                request.user.is_staff or
                request.user.is_superuser
            )
        )
        is_team_coach = False
        if request.user.is_authenticated:
            coached_team = getattr(request.user, 'get_coached_batch_team', lambda: None)()
            if coached_team and coached_team.id == team.id:
                is_team_coach = True
            elif team.coach_user_id and team.coach_user_id == request.user.id:
                is_team_coach = True
            elif team.coach_member_id and getattr(request.user, 'linked_member_id', None) == team.coach_member_id:
                is_team_coach = True

        if not (is_mgr or is_team_coach):
            return Response(
                {"error": "You do not have permission to edit this batch profile. Only tournament managers and the batch coach can update it."},
                status=status.HTTP_403_FORBIDDEN
            )
        
        for field in ['name', 'nickname', 'motto', 'description', 'color_hex', 'team_photo_url', 'logo_url']:
            if field in request.data:
                setattr(team, field, request.data[field])
        
        team.save()

        AuditLog.objects.create(
            user=request.user,
            action_type='UPDATE',
            model_name='BatchTeam',
            object_id=str(team.id),
            object_repr=f"{team.name} ({team.batch_code})",
            notes=f"Batch profile updated by {'manager' if is_mgr else 'coach'} {request.user.username}."
        )

        return Response({
            'message': f"Batch team {team.name} updated successfully.",
            'team': BatchTeamSerializer(team).data
        })

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
                'is_coach': reg.member.is_coach,
            } for reg in roster_entries
        ]

        # All fellowship members in this batch
        if team.batch_code == 'OTHER':
            members_qs = MemberProfile.objects.filter(
                Q(academic_year='Other') | Q(competing_batch='OTHER'),
                is_approved=True
            )
        else:
            members_qs = MemberProfile.objects.filter(competing_batch=team.batch_code, is_approved=True)

        total_members = members_qs.count()

        # Map approved roster players for cross-referencing
        roster_by_member_id = {reg.member_id: reg for reg in roster_entries}
        registered_members = []
        for m in members_qs.select_related('user').order_by('first_name', 'second_name'):
            reg = roster_by_member_id.get(m.id)
            registered_members.append({
                'id': m.id,
                'username': m.user.username if m.user else '',
                'full_name': m.full_name,
                'first_name': m.first_name,
                'second_name': m.second_name,
                'department': m.department,
                'college': m.college,
                'academic_year': m.academic_year,
                'fellowship_team': m.fellowship_team,
                'gender': m.gender,
                'primary_position': m.primary_position,
                'secondary_position': m.secondary_position,
                'preferred_jersey_number': m.preferred_jersey_number,
                'profile_picture': m.avatar_url,
                'avatar_url': m.avatar_url,
                'profile_picture_url': m.profile_picture_url,
                'personal_chant': m.personal_chant,
                'is_coach': m.is_coach,
                'coached_batch_name': m.coached_batch_name,
                'is_on_roster': bool(reg),
                'roster_jersey_number': reg.jersey_number if reg else None,
                'roster_position': reg.preferred_position if reg else None,
            })

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
            'registered_members': registered_members,
            'roster': roster,
            'standing': team_standing,
            'fixtures': fixtures,
            'results': results,
        })

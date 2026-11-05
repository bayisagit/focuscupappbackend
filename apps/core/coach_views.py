from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db import transaction, models
from django.utils import timezone

from apps.competitions.models import BatchTeam, Season
from apps.matches.models import Match, MatchSquad, AuditLog
from apps.members.models import MemberProfile, PlayerRegistration
from apps.core.permissions import IsBatchCoach


def get_coach_context(user):
    """
    Helper to resolve the coached BatchTeam and the real MemberProfile of the coach.
    """
    if not getattr(user, 'is_coach', False):
        return None, None

    team = None
    if hasattr(user, 'coached_batch_team') and user.coached_batch_team:
        team = user.coached_batch_team
    elif hasattr(user, 'coached_teams'):
        team = user.coached_teams.first()

    member = getattr(user, 'linked_member', None)
    if not member and team and team.coach_member:
        member = team.coach_member

    return team, member


class CoachDashboardAPIView(APIView):
    """
    Summary metrics and team status for the authenticated batch coach.
    """
    permission_classes = [IsBatchCoach]

    def get(self, request):
        team, member = get_coach_context(request.user)
        if not team:
            return Response(
                {"error": "No batch team assignment found for this coach account."},
                status=status.HTTP_403_FORBIDDEN
            )

        active_season = Season.objects.filter(is_active=True).first()

        # Roster stats
        pending_apps = PlayerRegistration.objects.filter(
            batch_team=team,
            status='PENDING'
        ).count()
        approved_squad = PlayerRegistration.objects.filter(
            batch_team=team,
            status='APPROVED'
        ).count()

        # Matches involving this batch
        matches_qs = Match.objects.filter(
            models.Q(home_team=team) | models.Q(away_team=team)
        ).select_related('home_team', 'away_team', 'season').order_by('match_date', 'kick_off_time')

        if active_season:
            matches_qs = matches_qs.filter(season=active_season)

        upcoming_matches = []
        next_match_data = None
        for m in matches_qs:
            is_home = (m.home_team_id == team.id)
            opponent = m.away_team if is_home else m.home_team
            squad_count = MatchSquad.objects.filter(match=m, team=team).count()
            starters_count = MatchSquad.objects.filter(match=m, team=team, is_starter=True).count()
            has_gk = MatchSquad.objects.filter(match=m, team=team, is_goalkeeper=True).exists()

            m_data = {
                'id': m.id,
                'round_number': m.round_number,
                'match_date': str(m.match_date),
                'kick_off_time': str(m.kick_off_time)[:5],
                'venue': m.venue,
                'status': m.status,
                'home_score': m.home_score,
                'away_score': m.away_score,
                'is_home': is_home,
                'opponent': {
                    'id': opponent.id,
                    'name': opponent.name,
                    'batch_code': opponent.batch_code,
                    'nickname': opponent.nickname,
                    'color_hex': opponent.color_hex,
                    'photo_url': opponent.photo_url,
                },
                'lineup_status': {
                    'is_submitted': squad_count > 0,
                    'total_players': squad_count,
                    'starters_count': starters_count,
                    'has_goalkeeper': has_gk,
                }
            }
            upcoming_matches.append(m_data)

            # Determine next active match
            if not next_match_data and m.status in ('SCHEDULED', 'LIVE', 'HALF_TIME'):
                next_match_data = m_data

        return Response({
            'team': {
                'id': team.id,
                'name': team.name,
                'batch_code': team.batch_code,
                'nickname': team.nickname,
                'color_hex': team.color_hex,
                'motto': team.motto,
                'photo_url': team.photo_url,
            },
            'coach_profile': {
                'username': request.user.username,
                'member_id': member.id if member else None,
                'full_name': member.full_name if member else request.user.get_full_name() or request.user.username,
                'avatar_url': member.avatar_url if member else None,
                'department': member.department if member else '',
                'academic_year': member.academic_year if member else '',
                'college': member.get_college_display() if member else '',
                'preferred_jersey_number': member.preferred_jersey_number if member else None,
            },
            'stats': {
                'pending_applications': pending_apps,
                'approved_players': approved_squad,
                'total_fixtures': len(upcoming_matches),
            },
            'next_match': next_match_data,
            'upcoming_matches': upcoming_matches[:5],
        })


class CoachPlayerRegistrationsAPIView(APIView):
    """
    List and filter player registrations for the coach's batch team.
    """
    permission_classes = [IsBatchCoach]

    def get(self, request):
        team, _ = get_coach_context(request.user)
        if not team:
            return Response({"error": "No batch team assignment found."}, status=status.HTTP_403_FORBIDDEN)

        status_filter = request.query_params.get('status')
        qs = PlayerRegistration.objects.filter(batch_team=team).select_related(
            'member', 'member__user', 'season', 'batch_team'
        ).order_by('-created_at')

        if status_filter:
            qs = qs.filter(status=status_filter)

        data = [
            {
                'id': reg.id,
                'member_id': reg.member.id,
                'full_name': reg.member.full_name,
                'first_name': reg.member.first_name,
                'second_name': reg.member.second_name,
                'username': reg.member.user.username,
                'college': reg.member.get_college_display(),
                'department': reg.member.department,
                'academic_year': reg.member.academic_year,
                'avatar_url': reg.member.avatar_url,
                'preferred_position': reg.preferred_position,
                'jersey_number': reg.jersey_number,
                'football_notes': reg.football_notes,
                'status': reg.status,
                'rejection_reason': reg.rejection_reason if reg.status == 'REJECTED' else None,
                'created_at': reg.created_at,
            }
            for reg in qs
        ]
        return Response(data)


class CoachPlayerReviewAPIView(APIView):
    """
    Approve or reject a player registration application for the coach's batch team.
    """
    permission_classes = [IsBatchCoach]

    def post(self, request, registration_id):
        team, coach_member = get_coach_context(request.user)
        if not team:
            return Response({"error": "No batch team assignment found."}, status=status.HTTP_403_FORBIDDEN)

        reg = get_object_or_404(
            PlayerRegistration.objects.select_related('member', 'member__user', 'batch_team', 'season'),
            id=registration_id,
            batch_team=team
        )

        new_status = request.data.get('status')
        reason = request.data.get('reason', '')
        new_jersey = request.data.get('jersey_number')

        if new_status not in ('APPROVED', 'REJECTED'):
            return Response({"error": "Status must be APPROVED or REJECTED."}, status=status.HTTP_400_BAD_REQUEST)

        if new_jersey is not None:
            try:
                j_val = int(new_jersey)
                if 1 <= j_val <= 99:
                    reg.jersey_number = j_val
            except (ValueError, TypeError):
                pass

        if new_status == 'APPROVED':
            conflict = PlayerRegistration.objects.filter(
                batch_team=reg.batch_team,
                season=reg.season,
                jersey_number=reg.jersey_number,
                status='APPROVED'
            ).exclude(id=reg.id).select_related('member').first()

            if conflict:
                taken_name = conflict.member.full_name if conflict.member else "another player"
                return Response({
                    "error": f"Cannot approve application: Jersey #{reg.jersey_number} is already assigned to {taken_name} in {reg.batch_team.name}. Please reassign jersey number before approving."
                }, status=status.HTTP_400_BAD_REQUEST)

        reg.status = new_status
        reg.reviewed_by = request.user
        reg.rejection_reason = reason
        reg.reviewed_at = timezone.now()
        reg.save()

        AuditLog.objects.create(
            user=request.user,
            action_type='UPDATE',
            model_name='PlayerRegistration',
            object_id=str(reg.id),
            object_repr=f"{reg.member.full_name} ({reg.batch_team.name})",
            notes=f"Player application {new_status.lower()} by Coach {coach_member.full_name if coach_member else request.user.username}."
        )

        return Response({
            "message": f"Player application for {reg.member.full_name} has been {new_status.lower()}.",
            "registration": {
                'id': reg.id,
                'status': reg.status,
                'jersey_number': reg.jersey_number,
                'rejection_reason': reg.rejection_reason,
            }
        })


class CoachMatchesAPIView(APIView):
    """
    List all fixtures involving the coach's batch team.
    """
    permission_classes = [IsBatchCoach]

    def get(self, request):
        team, _ = get_coach_context(request.user)
        if not team:
            return Response({"error": "No batch team assignment found."}, status=status.HTTP_403_FORBIDDEN)

        matches = Match.objects.filter(
            models.Q(home_team=team) | models.Q(away_team=team)
        ).select_related('home_team', 'away_team', 'season').order_by('match_date', 'kick_off_time')

        data = []
        for m in matches:
            is_home = (m.home_team_id == team.id)
            opponent = m.away_team if is_home else m.home_team
            squad_count = MatchSquad.objects.filter(match=m, team=team).count()
            starters_count = MatchSquad.objects.filter(match=m, team=team, is_starter=True).count()
            has_gk = MatchSquad.objects.filter(match=m, team=team, is_goalkeeper=True).exists()

            data.append({
                'id': m.id,
                'round_number': m.round_number,
                'match_date': str(m.match_date),
                'kick_off_time': str(m.kick_off_time)[:5],
                'venue': m.venue,
                'status': m.status,
                'home_score': m.home_score,
                'away_score': m.away_score,
                'is_home': is_home,
                'team': {
                    'id': team.id,
                    'name': team.name,
                    'batch_code': team.batch_code,
                    'color_hex': team.color_hex,
                    'photo_url': team.photo_url,
                },
                'opponent': {
                    'id': opponent.id,
                    'name': opponent.name,
                    'batch_code': opponent.batch_code,
                    'color_hex': opponent.color_hex,
                    'photo_url': opponent.photo_url,
                },
                'lineup_submitted': squad_count > 0,
                'starters_count': starters_count,
                'total_squad_count': squad_count,
                'has_goalkeeper': has_gk,
            })
        return Response(data)


class CoachMatchSquadAPIView(APIView):
    """
    Get eligible players and submit the official starting line-up for the coach's batch team.
    When saved, MatchSquad is immediately updated so the manager sees the line-up in real time.
    """
    permission_classes = [IsBatchCoach]

    def get(self, request, match_id):
        team, coach_member = get_coach_context(request.user)
        if not team:
            return Response({"error": "No batch team assignment found."}, status=status.HTTP_403_FORBIDDEN)

        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team', 'season'),
            pk=match_id
        )

        if match.home_team_id != team.id and match.away_team_id != team.id:
            return Response({"error": "Your batch team is not scheduled for this fixture."}, status=status.HTTP_403_FORBIDDEN)

        is_home = (match.home_team_id == team.id)
        opponent = match.away_team if is_home else match.home_team

        # Eligible players for coach's team
        # 1. Registered & approved players
        reg_players = PlayerRegistration.objects.filter(
            batch_team=team,
            status='APPROVED'
        ).select_related('member', 'member__user')

        seen_member_ids = set()
        eligible_players = []

        for reg in reg_players:
            m = reg.member
            seen_member_ids.add(m.id)
            is_coach_player = bool(coach_member and coach_member.id == m.id)
            eligible_players.append({
                'id': m.id,
                'member_id': m.id,
                'full_name': m.full_name,
                'first_name': m.first_name,
                'second_name': m.second_name,
                'username': m.user.username,
                'position': reg.preferred_position or m.primary_position or 'Player',
                'jersey_number': reg.jersey_number or m.preferred_jersey_number or None,
                'department': m.department,
                'academic_year': m.academic_year,
                'avatar_url': m.avatar_url,
                'is_coach_player': is_coach_player,
                'is_approved_registration': True,
            })

        # 2. Add coach himself if not in player registration list yet
        if coach_member and coach_member.id not in seen_member_ids:
            seen_member_ids.add(coach_member.id)
            eligible_players.append({
                'id': coach_member.id,
                'member_id': coach_member.id,
                'full_name': coach_member.full_name,
                'first_name': coach_member.first_name,
                'second_name': coach_member.second_name,
                'username': getattr(coach_member.user, 'username', 'coach'),
                'position': coach_member.primary_position or 'Player',
                'jersey_number': coach_member.preferred_jersey_number or None,
                'department': coach_member.department,
                'academic_year': coach_member.academic_year,
                'avatar_url': coach_member.avatar_url,
                'is_coach_player': True,
                'is_approved_registration': True,
            })

        # 3. Fallback approved batch members
        fallback_members = MemberProfile.objects.filter(
            competing_batch=team.batch_code,
            is_suspended=False
        ).exclude(id__in=seen_member_ids).select_related('user')

        for m in fallback_members:
            eligible_players.append({
                'id': m.id,
                'member_id': m.id,
                'full_name': m.full_name,
                'first_name': m.first_name,
                'second_name': m.second_name,
                'username': m.user.username,
                'position': m.primary_position or 'Player',
                'jersey_number': m.preferred_jersey_number or None,
                'department': m.department,
                'academic_year': m.academic_year,
                'avatar_url': m.avatar_url,
                'is_coach_player': False,
                'is_approved_registration': False,
            })

        eligible_players.sort(key=lambda p: (0 if p.get('is_coach_player') else 1, 0 if p['is_approved_registration'] else 1, p['full_name']))

        # Current squad selections for coach's team
        current_squad_entries = MatchSquad.objects.filter(
            match=match,
            team=team
        ).select_related('player', 'player__user')

        squad_list = [
            {
                'id': s.id,
                'player_id': s.player_id,
                'player_name': s.player.full_name,
                'first_name': s.player.first_name,
                'second_name': s.player.second_name,
                'player_username': s.player.user.username,
                'jersey_number': s.jersey_number,
                'is_starter': s.is_starter,
                'is_goalkeeper': s.is_goalkeeper,
                'position': s.player.primary_position or 'Player',
                'avatar_url': s.player.avatar_url,
                'is_coach_player': bool(coach_member and coach_member.id == s.player_id),
            }
            for s in current_squad_entries
        ]

        # Opponent lineup overview (starters count & list if submitted)
        opp_entries = MatchSquad.objects.filter(
            match=match,
            team=opponent
        ).select_related('player')
        opp_squad_list = [
            {
                'player_name': s.player.full_name,
                'jersey_number': s.jersey_number,
                'is_starter': s.is_starter,
                'is_goalkeeper': s.is_goalkeeper,
            }
            for s in opp_entries
        ]

        return Response({
            'match': {
                'id': match.id,
                'round_number': match.round_number,
                'match_date': str(match.match_date),
                'kick_off_time': str(match.kick_off_time)[:5],
                'venue': match.venue,
                'status': match.status,
                'is_home': is_home,
                'team': {
                    'id': team.id,
                    'name': team.name,
                    'batch_code': team.batch_code,
                    'color_hex': team.color_hex,
                    'photo_url': team.photo_url,
                },
                'opponent': {
                    'id': opponent.id,
                    'name': opponent.name,
                    'batch_code': opponent.batch_code,
                    'color_hex': opponent.color_hex,
                    'photo_url': opponent.photo_url,
                },
            },
            'eligible_players': eligible_players,
            'current_squad': squad_list,
            'opponent_squad': opp_squad_list,
            'coach_member': {
                'id': coach_member.id if coach_member else None,
                'full_name': coach_member.full_name if coach_member else request.user.username,
            }
        })

    def post(self, request, match_id):
        team, coach_member = get_coach_context(request.user)
        if not team:
            return Response({"error": "No batch team assignment found."}, status=status.HTTP_403_FORBIDDEN)

        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team'),
            pk=match_id
        )

        if match.home_team_id != team.id and match.away_team_id != team.id:
            return Response({"error": "Your batch team is not participating in this match."}, status=status.HTTP_403_FORBIDDEN)

        squad_data = request.data.get('squad')
        if squad_data is None:
            return Response({"error": "No squad data provided."}, status=status.HTTP_400_BAD_REQUEST)

        # Validate unique players
        player_ids = [item.get('player_id') or item.get('player') for item in squad_data if item.get('player_id') or item.get('player')]
        if len(player_ids) != len(set(player_ids)):
            return Response({"error": "Duplicate players detected in submitted squad list."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            # Delete previous squad entries for this match and team
            MatchSquad.objects.filter(match=match, team=team).delete()

            for item in squad_data:
                player_id = item.get('player_id') or item.get('player')
                player = MemberProfile.objects.filter(pk=player_id).first()
                if player:
                    if not player.competing_batch:
                        player.competing_batch = team.batch_code
                        player.save(update_fields=['competing_batch'])

                    jersey = item.get('jersey_number') or player.preferred_jersey_number or 99
                    MatchSquad.objects.create(
                        match=match,
                        team=team,
                        player=player,
                        jersey_number=int(jersey),
                        is_starter=bool(item.get('is_starter', True)),
                        is_goalkeeper=bool(item.get('is_goalkeeper', False)),
                    )

            coach_label = coach_member.full_name if coach_member else request.user.username
            AuditLog.objects.create(
                user=request.user,
                action_type='UPDATE',
                model_name='MatchSquad',
                object_id=str(match.id),
                object_repr=f"{match.home_team.name} vs {match.away_team.name}",
                notes=f"Official match squad ({len(squad_data)} players) submitted by Coach {coach_label} for {team.name}."
            )

        saved_entries = MatchSquad.objects.filter(match=match, team=team).select_related('player')
        return Response({
            "message": f"Official line-up for {team.name} has been saved successfully!",
            "starters_count": saved_entries.filter(is_starter=True).count(),
            "subs_count": saved_entries.filter(is_starter=False).count(),
            "has_goalkeeper": saved_entries.filter(is_goalkeeper=True).exists(),
            "squad": [
                {
                    'id': s.id,
                    'player_id': s.player_id,
                    'player_name': s.player.full_name,
                    'jersey_number': s.jersey_number,
                    'is_starter': s.is_starter,
                    'is_goalkeeper': s.is_goalkeeper,
                }
                for s in saved_entries
            ]
        }, status=status.HTTP_200_OK)

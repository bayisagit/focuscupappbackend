import csv
import json
from django.http import HttpResponse
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, generics
from rest_framework.views import APIView
from rest_framework.response import Response

from apps.core.permissions import IsTournamentManager
from apps.accounts.models import CustomUser
from apps.members.models import MemberProfile, PlayerRegistration
from apps.competitions.models import Season, BatchTeam
from apps.competitions.services import generate_round_robin_fixtures
from apps.matches.models import Match, MatchSquad, MatchEvent, AuditLog
from apps.community.models import Notification
from apps.statistics.services import (
    calculate_season_standings,
    get_tournament_summary,
    get_active_season,
)


class ManagerDashboardAPIView(APIView):
    """Provides high-level management statistics, distributions, and recent activity."""
    permission_classes = [IsTournamentManager]

    def get(self, request):
        season = get_active_season()
        summary = get_tournament_summary(season.id if season else None)

        # Batch distribution
        batch_counts = (
            MemberProfile.objects.filter(is_approved=True)
            .values('competing_batch')
            .annotate(count=Count('id'))
            .order_by('competing_batch')
        )
        batch_map = {
            '2ND_YEAR': '2nd Year',
            '3RD_YEAR': '3rd Year',
            '4TH_YEAR': '4th Year',
            '5TH_YEAR': '5th Year',
            'OTHER': 'Other',
        }
        members_by_batch = [
            {'batch': batch_map.get(b['competing_batch'], b['competing_batch'] or 'Other'), 'count': b['count']}
            for b in batch_counts
        ]

        # Gender distribution
        gender_counts = (
            MemberProfile.objects.filter(is_approved=True)
            .values('gender')
            .annotate(count=Count('id'))
        )

        # College distribution
        college_counts = (
            MemberProfile.objects.filter(is_approved=True)
            .values('college')
            .annotate(count=Count('id'))
        )

        # Pending player applications
        pending_applications = PlayerRegistration.objects.filter(status='PENDING').count()

        # Recent registrations
        recent_members = (
            MemberProfile.objects.select_related('user')
            .order_by('-created_at')[:8]
        )
        recent_members_data = [
            {
                'id': m.id,
                'username': m.user.username,
                'email': m.user.email,
                'full_name': m.full_name,
                'batch': m.get_competing_batch_display() or m.academic_year,
                'department': m.department,
                'profile_picture': m.avatar_url,
                'avatar_url': m.avatar_url,
                'profile_picture_url': m.profile_picture_url,
                'created_at': m.created_at,
            } for m in recent_members
        ]

        # Recent audit logs
        recent_logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:10]
        recent_logs_data = [
            {
                'id': l.id,
                'user': l.user.username if l.user else 'System',
                'action_type': l.get_action_type_display(),
                'model_name': l.model_name,
                'object_repr': l.object_repr,
                'notes': l.notes,
                'timestamp': l.timestamp,
            } for l in recent_logs
        ]

        return Response({
            'kpis': summary,
            'pending_applications': pending_applications,
            'members_by_batch': members_by_batch,
            'gender_distribution': list(gender_counts),
            'college_distribution': list(college_counts),
            'recent_members': recent_members_data,
            'recent_activity': recent_logs_data,
        })


class ManagerMemberListAPIView(generics.ListAPIView):
    """Full member directory for administrators including email and account status."""
    permission_classes = [IsTournamentManager]

    def get(self, request):
        qs = MemberProfile.objects.select_related('user').all()

        search = request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(second_name__icontains=search) |
                Q(user__username__icontains=search) |
                Q(user__email__icontains=search) |
                Q(department__icontains=search)
            )

        batch = request.query_params.get('batch')
        if batch:
            batch_clean = batch.strip()
            batch_code = None
            if '2' in batch_clean: batch_code = '2ND_YEAR'
            elif '3' in batch_clean: batch_code = '3RD_YEAR'
            elif '4' in batch_clean: batch_code = '4TH_YEAR'
            elif '5' in batch_clean: batch_code = '5TH_YEAR'

            cond = Q(academic_year__icontains=batch_clean) | Q(competing_batch__iexact=batch_clean)
            if batch_code:
                cond |= Q(competing_batch=batch_code)
            if batch_clean.lower() == 'other':
                cond |= Q(competing_batch__isnull=True) | Q(academic_year__icontains='other') | Q(academic_year__icontains='1st')
            qs = qs.filter(cond)

        college = request.query_params.get('college')
        if college:
            qs = qs.filter(college=college)

        members_data = [
            {
                'id': m.id,
                'user_id': m.user.id,
                'username': m.user.username,
                'email': m.user.email,
                'first_name': m.first_name,
                'second_name': m.second_name,
                'full_name': m.full_name,
                'college': m.get_college_display(),
                'department': m.department,
                'academic_year': m.academic_year,
                'competing_batch': m.competing_batch,
                'batch_code': m.competing_batch,
                'batch': m.get_competing_batch_display() or m.academic_year,
                'fellowship_team': m.fellowship_team,
                'gender': m.gender,
                'primary_position': m.primary_position,
                'preferred_jersey_number': m.preferred_jersey_number,
                'profile_picture': m.avatar_url,
                'avatar_url': m.avatar_url,
                'profile_picture_url': m.profile_picture_url,
                'is_football_eligible': m.is_football_eligible,
                'is_suspended': m.is_suspended,
                'is_active': (not m.is_suspended) and m.user.is_active,
                'followers_count': m.followers_count,
                'created_at': m.created_at,
            } for m in qs.order_by('-created_at')
        ]
        return Response(members_data)


class ManagerMemberSuspendToggleAPIView(APIView):
    """Suspend or reactivate a fellowship member account."""
    permission_classes = [IsTournamentManager]

    def post(self, request, member_id):
        profile = get_object_or_404(MemberProfile.objects.select_related('user'), id=member_id)
        profile.is_suspended = not profile.is_suspended
        profile.user.is_active = not profile.is_suspended
        profile.user.save(update_fields=['is_active'])
        profile.save(update_fields=['is_suspended'])

        action = 'SUSPEND_MEMBER' if profile.is_suspended else 'REACTIVATE_MEMBER'
        status_text = "suspended" if profile.is_suspended else "reactivated"

        AuditLog.objects.create(
            user=request.user,
            action_type=action,
            model_name='MemberProfile',
            object_id=str(profile.id),
            object_repr=profile.full_name,
            notes=f"Account {status_text} by manager {request.user.username}."
        )

        return Response({
            'message': f"Account for {profile.full_name} is now {status_text}.",
            'is_suspended': profile.is_suspended,
            'is_active': not profile.is_suspended,
        })


class ManagerMemberDeleteAPIView(APIView):
    """Permanently delete a fellowship member profile and auth user account."""
    permission_classes = [IsTournamentManager]

    def delete(self, request, member_id):
        profile = get_object_or_404(MemberProfile.objects.select_related('user'), id=member_id)
        target_user = profile.user

        if target_user == request.user:
            return Response(
                {'error': 'You cannot delete your own manager account.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if target_user.is_superuser:
            return Response(
                {'error': 'Superuser accounts cannot be deleted from the tournament portal.'},
                status=status.HTTP_403_FORBIDDEN
            )

        member_name = profile.full_name
        username = target_user.username

        AuditLog.objects.create(
            user=request.user,
            action_type='DELETE',
            model_name='MemberProfile',
            object_id=str(profile.id),
            object_repr=member_name,
            notes=f"Member profile {member_name} (@{username}) deleted permanently by manager {request.user.username}."
        )

        # Deleting the CustomUser cascades cleanly to MemberProfile, PlayerRegistration, etc.
        target_user.delete()

        return Response({
            'message': f'Member "{member_name}" (@{username}) has been permanently deleted.',
            'deleted_id': member_id,
        })


class ManagerPlayerRegistrationsAPIView(APIView):
    """List all player applications for roster approval."""
    permission_classes = [IsTournamentManager]

    def get(self, request):
        status_filter = request.query_params.get('status')
        qs = (
            PlayerRegistration.objects.select_related('member', 'member__user', 'season', 'batch_team')
            .all()
        )
        if status_filter:
            qs = qs.filter(status=status_filter)

        data = [
            {
                'id': reg.id,
                'member_id': reg.member.id,
                'full_name': reg.member.full_name or reg.member.user.get_full_name() or reg.member.user.username,
                'member_name': reg.member.full_name or reg.member.user.get_full_name() or reg.member.user.username,
                'first_name': reg.member.first_name,
                'second_name': reg.member.second_name,
                'username': reg.member.user.username,
                'email': reg.member.user.email,
                'college': reg.member.college,
                'department': reg.member.department,
                'academic_year': reg.member.academic_year,
                'fellowship_team': reg.member.fellowship_team,
                'gender': reg.member.gender,
                'avatar_url': reg.member.avatar_url,
                'profile_picture_url': reg.member.profile_picture_url,
                'batch_name': reg.batch_team.name,
                'batch_code': reg.batch_team.batch_code,
                'preferred_position': reg.preferred_position,
                'football_position': reg.preferred_position,
                'jersey_number': reg.jersey_number,
                'status': reg.status,
                'football_notes': reg.football_notes,
                'created_at': reg.created_at,
            } for reg in qs.order_by('-created_at')
        ]
        return Response(data)


class ManagerPlayerReviewAPIView(APIView):
    """Approve or reject a player's roster application."""
    permission_classes = [IsTournamentManager]

    def post(self, request, registration_id):
        reg = get_object_or_404(
            PlayerRegistration.objects.select_related('member', 'member__user', 'batch_team'),
            id=registration_id
        )
        new_status = request.data.get('status')
        reason = request.data.get('reason', '')

        if new_status not in ('APPROVED', 'REJECTED'):
            return Response({"error": "Status must be APPROVED or REJECTED."}, status=status.HTTP_400_BAD_REQUEST)

        reg.status = new_status
        reg.reviewed_by = request.user
        reg.rejection_reason = reason
        reg.save()

        action = 'APPROVE_PLAYER' if new_status == 'APPROVED' else 'REJECT_PLAYER'
        AuditLog.objects.create(
            user=request.user,
            action_type=action,
            model_name='PlayerRegistration',
            object_id=str(reg.id),
            object_repr=f"{reg.member.full_name} (#{reg.jersey_number}) - {reg.batch_team.name}",
            notes=f"Player application marked {new_status}. {reason}"
        )

        # Notify member
        Notification.objects.create(
            recipient=reg.member.user,
            actor=request.user,
            verb=f"Your tournament player registration for {reg.batch_team.name} has been {new_status.lower()}.",
            target_url=f"/batches/{reg.batch_team.batch_code}"
        )

        return Response({
            'message': f"Application {new_status.lower()} successfully.",
            'status': reg.status,
        })


class ManagerGenerateFixturesAPIView(APIView):
    """Automatically generates single round-robin fixtures for competing batches."""
    permission_classes = [IsTournamentManager]

    def post(self, request):
        season_id = request.data.get('season_id')
        season = Season.objects.filter(pk=season_id).first() if season_id else get_active_season()
        if not season:
            return Response({"error": "No season found."}, status=status.HTTP_400_BAD_REQUEST)

        start_date = request.data.get('start_date')
        count, msg = generate_round_robin_fixtures(season=season, start_date=start_date)

        AuditLog.objects.create(
            user=request.user,
            action_type='CREATE',
            model_name='Match',
            object_id=str(season.id),
            object_repr=season.name,
            notes=f"Generated {count} round-robin fixtures automatically."
        )

        return Response({'message': msg, 'fixtures_created': count})


class ManagerCreateFixtureAPIView(APIView):
    """Allows tournament managers to manually create custom fixtures (e.g., Finals, Semi-finals, special matchdays)."""
    permission_classes = [IsTournamentManager]

    def post(self, request):
        home_team_id = request.data.get('home_team_id')
        away_team_id = request.data.get('away_team_id')
        match_date = request.data.get('match_date')
        kick_off_time = request.data.get('kick_off_time', '16:00')
        venue = request.data.get('venue', 'AASTU Main Football Field')
        round_number = request.data.get('round_number', 1)
        stage_or_round_name = request.data.get('stage_or_round_name', 'Finals')
        notes = request.data.get('notes', '')

        if not home_team_id or not away_team_id:
            return Response({"error": "Please select both competing batch teams."}, status=status.HTTP_400_BAD_REQUEST)

        home_team = (
            BatchTeam.objects.filter(id=home_team_id).first()
            if str(home_team_id).isdigit()
            else BatchTeam.objects.filter(batch_code=home_team_id).first()
        )
        away_team = (
            BatchTeam.objects.filter(id=away_team_id).first()
            if str(away_team_id).isdigit()
            else BatchTeam.objects.filter(batch_code=away_team_id).first()
        )

        if not home_team or not away_team:
            return Response({"error": "One or both selected teams could not be found."}, status=status.HTTP_404_NOT_FOUND)

        if home_team.id == away_team.id:
            return Response({"error": "A batch team cannot play against itself."}, status=status.HTTP_400_BAD_REQUEST)

        if not match_date:
            return Response({"error": "Match competition date is required."}, status=status.HTTP_400_BAD_REQUEST)

        season = get_active_season()
        if not season:
            season = Season.objects.first()

        match_report_combined = f"[{stage_or_round_name}] {notes}".strip()

        match = Match.objects.create(
            season=season,
            round_number=int(round_number) if str(round_number).isdigit() else 1,
            home_team=home_team,
            away_team=away_team,
            match_date=match_date,
            kick_off_time=kick_off_time or '16:00',
            venue=venue or 'AASTU Main Football Field',
            status='SCHEDULED',
            match_report=match_report_combined,
            created_by=request.user,
        )

        AuditLog.objects.create(
            user=request.user,
            action_type='CREATE',
            model_name='Match',
            object_id=str(match.id),
            object_repr=f"{home_team.name} vs {away_team.name}",
            notes=f"Manually created fixture ({stage_or_round_name}) scheduled for {match_date} at {kick_off_time}."
        )

        return Response({
            'message': f"Fixture created successfully! {home_team.name} vs {away_team.name} ({stage_or_round_name}) on {match_date}.",
            'match_id': match.id
        }, status=status.HTTP_201_CREATED)


class ManagerMatchUpdateAPIView(APIView):
    """
    Update fixture schedule, venue, status, competing batch teams, draft score, or match report.
    Allows managers to reschedule, postpone, cancel, or modify tournament fixtures.
    """
    permission_classes = [IsTournamentManager]

    def patch(self, request, match_id):
        return self._update(request, match_id)

    def put(self, request, match_id):
        return self._update(request, match_id)

    def _update(self, request, match_id):
        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team', 'season'),
            pk=match_id
        )

        match_date = request.data.get('match_date')
        kick_off_time = request.data.get('kick_off_time')
        venue = request.data.get('venue')
        round_number = request.data.get('round_number')
        home_team_id = request.data.get('home_team_id')
        away_team_id = request.data.get('away_team_id')
        home_score = request.data.get('home_score')
        away_score = request.data.get('away_score')
        match_status = request.data.get('status')
        match_report = request.data.get('match_report')
        stage_or_round_name = request.data.get('stage_or_round_name')
        notes = request.data.get('notes')
        potm_id = request.data.get('player_of_the_match_id')

        # Competing team modifications
        if home_team_id is not None:
            new_home = (
                BatchTeam.objects.filter(id=home_team_id).first()
                if str(home_team_id).isdigit()
                else BatchTeam.objects.filter(batch_code=home_team_id).first()
            )
            if new_home:
                match.home_team = new_home

        if away_team_id is not None:
            new_away = (
                BatchTeam.objects.filter(id=away_team_id).first()
                if str(away_team_id).isdigit()
                else BatchTeam.objects.filter(batch_code=away_team_id).first()
            )
            if new_away:
                match.away_team = new_away

        if match.home_team_id == match.away_team_id:
            return Response(
                {"error": "Home team and away team cannot be the same batch."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if match_date:
            match.match_date = match_date
        if kick_off_time:
            match.kick_off_time = kick_off_time
        if venue:
            match.venue = venue
        if round_number is not None and str(round_number).isdigit():
            match.round_number = int(round_number)
        if home_score is not None:
            match.home_score = int(home_score)
        if away_score is not None:
            match.away_score = int(away_score)
        if match_status:
            match.status = match_status

        if stage_or_round_name or notes:
            stage = stage_or_round_name or ''
            note_text = notes or ''
            if stage:
                match.match_report = f"[{stage}] {note_text}".strip()
            elif note_text:
                match.match_report = note_text
        elif match_report is not None:
            match.match_report = match_report

        if potm_id:
            match.player_of_the_match = MemberProfile.objects.filter(pk=potm_id).first()
        elif potm_id == '':
            match.player_of_the_match = None

        match.updated_by = request.user
        match.save()

        AuditLog.objects.create(
            user=request.user,
            action_type='UPDATE',
            model_name='Match',
            object_id=str(match.id),
            object_repr=f"{match.home_team.name} vs {match.away_team.name}",
            notes=f"Fixture #{match.id} schedule / details updated by manager {request.user.username}."
        )

        return Response({
            'message': f"Fixture #{match.id} updated successfully.",
            'id': match.id,
            'match_date': str(match.match_date),
            'kick_off_time': str(match.kick_off_time)[:5],
            'venue': match.venue,
            'round_number': match.round_number,
            'home_team': {
                'id': match.home_team.id,
                'name': match.home_team.name,
                'batch_code': match.home_team.batch_code,
                'nickname': match.home_team.nickname,
            },
            'away_team': {
                'id': match.away_team.id,
                'name': match.away_team.name,
                'batch_code': match.away_team.batch_code,
                'nickname': match.away_team.nickname,
            },
            'home_score': match.home_score,
            'away_score': match.away_score,
            'status': match.status,
            'match_report': match.match_report,
        })


class ManagerMatchSquadAPIView(APIView):
    """
    Manage team squad selections and starting line-ups for a match.
    GET: Retrieve available eligible batch players and current squad selections.
    POST / PUT: Save official team line-ups (starters, goalkeeper, substitutes, jersey numbers).
    """
    permission_classes = [IsTournamentManager]

    def get(self, request, match_id):
        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team', 'season'),
            pk=match_id
        )

        def get_team_eligible_players(team):
            reg_players = PlayerRegistration.objects.filter(
                batch_team=team,
                status='APPROVED'
            ).select_related('member', 'member__user')

            seen_member_ids = set()
            players_list = []

            for reg in reg_players:
                m = reg.member
                seen_member_ids.add(m.id)
                players_list.append({
                    'id': m.id,
                    'member_id': m.id,
                    'full_name': m.full_name,
                    'username': m.user.username,
                    'position': reg.preferred_position or m.primary_position or 'Player',
                    'jersey_number': reg.jersey_number or m.preferred_jersey_number or None,
                    'department': m.department,
                    'academic_year': m.academic_year,
                    'avatar_url': m.profile_picture_url or (m.profile_picture.url if m.profile_picture else None),
                    'is_approved_registration': True,
                })

            fallback_members = MemberProfile.objects.filter(
                competing_batch=team.batch_code,
                is_suspended=False
            ).exclude(id__in=seen_member_ids).select_related('user')

            for m in fallback_members:
                players_list.append({
                    'id': m.id,
                    'member_id': m.id,
                    'full_name': m.full_name,
                    'username': m.user.username,
                    'position': m.primary_position or 'Player',
                    'jersey_number': m.preferred_jersey_number or None,
                    'department': m.department,
                    'academic_year': m.academic_year,
                    'avatar_url': m.profile_picture_url or (m.profile_picture.url if m.profile_picture else None),
                    'is_approved_registration': False,
                })

            players_list.sort(key=lambda p: (0 if p['is_approved_registration'] else 1, p['full_name']))
            return players_list

        home_eligible = get_team_eligible_players(match.home_team)
        away_eligible = get_team_eligible_players(match.away_team)

        home_squad_entries = MatchSquad.objects.filter(
            match=match,
            team=match.home_team
        ).select_related('player', 'player__user')

        away_squad_entries = MatchSquad.objects.filter(
            match=match,
            team=match.away_team
        ).select_related('player', 'player__user')

        def serialize_squad(entries):
            return [
                {
                    'id': s.id,
                    'player_id': s.player_id,
                    'player_name': s.player.full_name,
                    'player_username': s.player.user.username,
                    'jersey_number': s.jersey_number,
                    'is_starter': s.is_starter,
                    'is_goalkeeper': s.is_goalkeeper,
                    'position': s.player.primary_position or 'Player',
                    'avatar_url': s.player.profile_picture_url or (s.player.profile_picture.url if s.player.profile_picture else None),
                }
                for s in entries
            ]

        return Response({
            'match': {
                'id': match.id,
                'round_number': match.round_number,
                'match_date': str(match.match_date),
                'kick_off_time': str(match.kick_off_time)[:5],
                'venue': match.venue,
                'status': match.status,
                'match_report': match.match_report,
                'home_team': {
                    'id': match.home_team.id,
                    'name': match.home_team.name,
                    'batch_code': match.home_team.batch_code,
                    'nickname': match.home_team.nickname,
                    'color_hex': match.home_team.color_hex,
                },
                'away_team': {
                    'id': match.away_team.id,
                    'name': match.away_team.name,
                    'batch_code': match.away_team.batch_code,
                    'nickname': match.away_team.nickname,
                    'color_hex': match.away_team.color_hex,
                },
            },
            'home_eligible_players': home_eligible,
            'away_eligible_players': away_eligible,
            'home_squad': serialize_squad(home_squad_entries),
            'away_squad': serialize_squad(away_squad_entries),
        })

    def post(self, request, match_id):
        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team'),
            pk=match_id
        )

        home_squad_data = request.data.get('home_squad')
        away_squad_data = request.data.get('away_squad')

        with transaction.atomic():
            if home_squad_data is not None:
                MatchSquad.objects.filter(match=match, team=match.home_team).delete()
                for item in home_squad_data:
                    player_id = item.get('player_id') or item.get('player')
                    player = MemberProfile.objects.filter(pk=player_id).first()
                    if player:
                        if not player.competing_batch:
                            player.competing_batch = match.home_team.batch_code
                            player.save(update_fields=['competing_batch'])
                        jersey = item.get('jersey_number') or player.preferred_jersey_number or 99
                        MatchSquad.objects.create(
                            match=match,
                            team=match.home_team,
                            player=player,
                            jersey_number=int(jersey),
                            is_starter=bool(item.get('is_starter', True)),
                            is_goalkeeper=bool(item.get('is_goalkeeper', False)),
                        )

            if away_squad_data is not None:
                MatchSquad.objects.filter(match=match, team=match.away_team).delete()
                for item in away_squad_data:
                    player_id = item.get('player_id') or item.get('player')
                    player = MemberProfile.objects.filter(pk=player_id).first()
                    if player:
                        if not player.competing_batch:
                            player.competing_batch = match.away_team.batch_code
                            player.save(update_fields=['competing_batch'])
                        jersey = item.get('jersey_number') or player.preferred_jersey_number or 99
                        MatchSquad.objects.create(
                            match=match,
                            team=match.away_team,
                            player=player,
                            jersey_number=int(jersey),
                            is_starter=bool(item.get('is_starter', True)),
                            is_goalkeeper=bool(item.get('is_goalkeeper', False)),
                        )

            AuditLog.objects.create(
                user=request.user,
                action_type='UPDATE',
                model_name='MatchSquad',
                object_id=str(match.id),
                object_repr=f"{match.home_team.name} vs {match.away_team.name}",
                notes=f"Manager {request.user.username} updated official match lineups/squads."
            )

        home_entries = MatchSquad.objects.filter(match=match, team=match.home_team).count()
        away_entries = MatchSquad.objects.filter(match=match, team=match.away_team).count()

        return Response({
            'message': f"Official match line-ups saved successfully! ({home_entries} {match.home_team.name} players, {away_entries} {match.away_team.name} players)",
            'home_count': home_entries,
            'away_count': away_entries,
        })


class ManagerMatchPublishAPIView(APIView):
    """
    Publishes a completed match result.
    Atomically ensures the match is COMPLETED and is_published=True,
    then updates the official standings and triggers an audit log.
    """
    permission_classes = [IsTournamentManager]

    def post(self, request, match_id):
        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team', 'season'),
            pk=match_id
        )

        with transaction.atomic():
            match.status = 'COMPLETED'
            match.is_published = True
            match.updated_by = request.user
            match.save()

            AuditLog.objects.create(
                user=request.user,
                action_type='PUBLISH',
                model_name='Match',
                object_id=str(match.id),
                object_repr=f"{match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}",
                notes=f"Match result published by manager {request.user.username}."
            )

        # Standings update dynamically because calculate_season_standings derives from published matches
        standings = calculate_season_standings(match.season_id)

        return Response({
            'message': f"Match result {match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name} published!",
            'is_published': match.is_published,
            'status': match.status,
            'updated_standings': standings,
        })


class ManagerMatchCorrectAPIView(APIView):
    """
    Corrects an official published result with full audit trail.
    """
    permission_classes = [IsTournamentManager]

    def post(self, request, match_id):
        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team', 'season'),
            pk=match_id
        )

        new_home_score = request.data.get('home_score')
        new_away_score = request.data.get('away_score')
        reason = request.data.get('reason', 'Score correction')

        if new_home_score is None or new_away_score is None:
            return Response({"error": "Both home_score and away_score are required."}, status=status.HTTP_400_BAD_REQUEST)

        old_repr = f"{match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}"

        with transaction.atomic():
            changes = {
                'old_score': f"{match.home_score} - {match.away_score}",
                'new_score': f"{new_home_score} - {new_away_score}",
                'reason': reason,
            }
            match.home_score = int(new_home_score)
            match.away_score = int(new_away_score)
            match.updated_by = request.user
            match.save()

            new_repr = f"{match.home_team.name} {match.home_score} - {match.away_score} {match.away_team.name}"
            AuditLog.objects.create(
                user=request.user,
                action_type='CORRECT',
                model_name='Match',
                object_id=str(match.id),
                object_repr=new_repr,
                changes=changes,
                notes=f"Score corrected from '{old_repr}' to '{new_repr}'. Reason: {reason}"
            )

        standings = calculate_season_standings(match.season_id)
        return Response({
            'message': f"Match score corrected to {new_repr}.",
            'changes': changes,
            'updated_standings': standings,
        })


class ManagerMatchEventAPIView(APIView):
    """Add or delete match events (goals, assists, cards, subs) with strict batch player validation."""
    permission_classes = [IsTournamentManager]

    def post(self, request, match_id):
        match = get_object_or_404(
            Match.objects.select_related('home_team', 'away_team'),
            pk=match_id
        )

        event_type = request.data.get('event_type')
        team_id = request.data.get('team_id')
        player_id = request.data.get('player_id')
        related_player_id = request.data.get('related_player_id')
        minute = int(request.data.get('minute', 1))
        extra_minute = request.data.get('extra_minute')
        description = request.data.get('description', '')

        # Validate team (with smart auto-inference from player's batch if team_id omitted)
        if not team_id and player_id:
            temp_p = MemberProfile.objects.filter(pk=player_id).first()
            if temp_p:
                if temp_p.competing_batch == match.home_team.batch_code:
                    team_id = match.home_team_id
                elif temp_p.competing_batch == match.away_team.batch_code:
                    team_id = match.away_team_id

        if not team_id:
            return Response({"error": "Please select which batch team (Home or Away) this incident applies to."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            team_id_int = int(team_id)
        except (ValueError, TypeError):
            return Response({"error": "Invalid team ID."}, status=status.HTTP_400_BAD_REQUEST)

        if team_id_int not in (match.home_team_id, match.away_team_id):
            return Response({"error": "Selected batch team is not playing in this match."}, status=status.HTTP_400_BAD_REQUEST)

        team = match.home_team if team_id_int == match.home_team_id else match.away_team

        # Validate player if provided
        player = None
        if player_id:
            player = get_object_or_404(MemberProfile, pk=player_id)
            if player.competing_batch != team.batch_code:
                return Response(
                    {"error": f"Player {player.full_name} belongs to batch {player.get_competing_batch_display()}, not {team.name}!"},
                    status=status.HTTP_400_BAD_REQUEST
                )

        related_player = None
        if related_player_id:
            related_player = MemberProfile.objects.filter(pk=related_player_id).first()

        with transaction.atomic():
            event = MatchEvent.objects.create(
                match=match,
                event_type=event_type,
                team=team,
                player=player,
                related_player=related_player,
                minute=minute,
                extra_minute=int(extra_minute) if extra_minute else None,
                description=description,
                created_by=request.user
            )

            # Auto-update score on goal
            if event_type == 'GOAL':
                if team == match.home_team:
                    match.home_score += 1
                else:
                    match.away_score += 1
                match.save(update_fields=['home_score', 'away_score'])

            elif event_type == 'OWN_GOAL':
                # Own goal increases the OPPONENT's score
                if team == match.home_team:
                    match.away_score += 1
                else:
                    match.home_score += 1
                match.save(update_fields=['home_score', 'away_score'])

        return Response({
            'message': f"Event '{event.get_event_type_display()}' recorded.",
            'event_id': event.id,
            'current_score': f"{match.home_score} - {match.away_score}",
        }, status=status.HTTP_201_CREATED)

    def delete(self, request, match_id):
        event_id = request.data.get('event_id')
        event = get_object_or_404(MatchEvent.objects.select_related('match', 'team'), pk=event_id, match_id=match_id)
        match = event.match

        with transaction.atomic():
            if event.event_type == 'GOAL':
                if event.team == match.home_team and match.home_score > 0:
                    match.home_score -= 1
                elif event.team == match.away_team and match.away_score > 0:
                    match.away_score -= 1
                match.save(update_fields=['home_score', 'away_score'])
            elif event.event_type == 'OWN_GOAL':
                if event.team == match.home_team and match.away_score > 0:
                    match.away_score -= 1
                elif event.team == match.away_team and match.home_score > 0:
                    match.home_score -= 1
                match.save(update_fields=['home_score', 'away_score'])

            event.delete()

        return Response({
            'message': 'Event deleted.',
            'current_score': f"{match.home_score} - {match.away_score}",
        })


class ManagerAuditLogListAPIView(generics.ListAPIView):
    """View administrative audit history."""
    permission_classes = [IsTournamentManager]

    def get(self, request):
        logs = AuditLog.objects.select_related('user').order_by('-timestamp')[:50]
        data = [
            {
                'id': l.id,
                'user': l.user.username if l.user else 'System',
                'action_type': l.get_action_type_display(),
                'model_name': l.model_name,
                'object_id': l.object_id,
                'object_repr': l.object_repr,
                'changes': l.changes,
                'notes': l.notes,
                'timestamp': l.timestamp,
            } for l in logs
        ]
        return Response(data)


class ManagerExportAPIView(APIView):
    """Export platform data to CSV format for tournament administration."""
    permission_classes = [IsTournamentManager]

    def perform_authentication(self, request):
        super().perform_authentication(request)
        # Fallback to query parameter token for direct browser downloads or <a download> links
        token = request.query_params.get('token')
        if (not request.user or not request.user.is_authenticated) and token:
            try:
                from rest_framework_simplejwt.tokens import AccessToken
                from django.contrib.auth import get_user_model
                access = AccessToken(token)
                User = get_user_model()
                user = User.objects.get(id=access['user_id'])
                if user.is_active and user.is_manager:
                    request.user = user
            except Exception:
                pass

    def get(self, request, data_type):
        response = HttpResponse(content_type='text/csv; charset=utf-8')
        response['Content-Disposition'] = f'attachment; filename="focus_cup_{data_type}.csv"'
        # Write UTF-8 BOM so Microsoft Excel and Google Sheets correctly recognize UTF-8 characters and columns
        response.write('\ufeff')
        writer = csv.writer(response)

        if data_type == 'members':
            writer.writerow([
                'ID', 'Username', 'Email', 'Full Name', 'College', 'Department',
                'Academic Year', 'Batch Team', 'Fellowship Team', 'Gender',
                'Primary Position', 'Eligible for Football', 'Approval Status', 'Followers Count'
            ])
            for m in MemberProfile.objects.select_related('user').order_by('id'):
                writer.writerow([
                    m.id,
                    m.user.username if m.user else '',
                    m.user.email if m.user else '',
                    m.full_name,
                    m.get_college_display(),
                    m.department,
                    m.academic_year,
                    m.get_competing_batch_display() if m.competing_batch else 'None',
                    m.fellowship_team,
                    m.gender,
                    m.primary_position or 'None',
                    'Yes' if m.is_football_eligible else 'No',
                    'Approved' if m.is_approved else 'Pending',
                    m.followers_count
                ])

        elif data_type == 'rosters':
            writer.writerow([
                'Registration ID', 'Season', 'Batch Team', 'Player Name', 'Username',
                'College', 'Department', 'Academic Year', 'Jersey Number', 'Position', 'Status', 'Registered At'
            ])
            for r in PlayerRegistration.objects.select_related('batch_team', 'member__user', 'season').order_by('batch_team__batch_code', 'jersey_number'):
                writer.writerow([
                    r.id,
                    r.season.name if r.season else '',
                    r.batch_team.name if r.batch_team else '',
                    r.member.full_name if r.member else '',
                    r.member.user.username if r.member and r.member.user else '',
                    r.member.get_college_display() if r.member else '',
                    r.member.department if r.member else '',
                    r.member.academic_year if r.member else '',
                    r.jersey_number,
                    r.preferred_position,
                    r.get_status_display() if hasattr(r, 'get_status_display') else r.status,
                    r.created_at.strftime('%Y-%m-%d %H:%M') if r.created_at else ''
                ])

        elif data_type == 'matches':
            writer.writerow([
                'Match ID', 'Season', 'Date', 'Time', 'Round', 'Venue',
                'Home Team', 'Away Team', 'Home Score', 'Away Score',
                'Scoreline', 'Status', 'Official Match Published'
            ])
            for m in Match.objects.select_related('home_team', 'away_team', 'season').order_by('match_date', 'kick_off_time'):
                scoreline = f"{m.home_score} - {m.away_score}" if m.status == 'COMPLETED' else 'vs'
                writer.writerow([
                    m.id,
                    m.season.name if m.season else '',
                    m.match_date,
                    m.kick_off_time.strftime('%H:%M') if m.kick_off_time else '',
                    f"Round {m.round_number}",
                    m.venue,
                    m.home_team.name if m.home_team else '',
                    m.away_team.name if m.away_team else '',
                    m.home_score if m.status == 'COMPLETED' else '',
                    m.away_score if m.status == 'COMPLETED' else '',
                    scoreline,
                    m.get_status_display() if hasattr(m, 'get_status_display') else m.status,
                    'Yes' if m.is_published else 'No'
                ])

        elif data_type == 'standings':
            writer.writerow([
                'Position', 'Batch Team', 'Nickname', 'Played (P)', 'Won (W)',
                'Drawn (D)', 'Lost (L)', 'Goals For (GF)', 'Goals Against (GA)',
                'Goal Difference (GD)', 'Points (Pts)'
            ])
            standings = calculate_season_standings()
            for s in standings:
                writer.writerow([
                    s['position'],
                    s['name'],
                    s.get('nickname') or '',
                    s['played'],
                    s['won'],
                    s['drawn'],
                    s['lost'],
                    s['goals_for'],
                    s['goals_against'],
                    s['goal_difference'],
                    s['points']
                ])

        else:
            return Response({"error": "Invalid export type. Choose members, rosters, matches, or standings."}, status=status.HTTP_400_BAD_REQUEST)

        # Record export action in audit log
        try:
            AuditLog.objects.create(
                user=request.user,
                action_type='EXPORT',
                model_name='Export',
                object_repr=f"Exported {data_type} CSV",
                notes=f"Generated {data_type} CSV report by {request.user.username}"
            )
        except Exception:
            pass

        return response

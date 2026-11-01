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
            qs = qs.filter(competing_batch=batch)

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
                'batch': m.get_competing_batch_display() or m.academic_year,
                'fellowship_team': m.fellowship_team,
                'gender': m.gender,
                'primary_position': m.primary_position,
                'preferred_jersey_number': m.preferred_jersey_number,
                'is_football_eligible': m.is_football_eligible,
                'is_suspended': m.is_suspended,
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
                'full_name': reg.member.full_name,
                'username': reg.member.user.username,
                'department': reg.member.department,
                'batch_name': reg.batch_team.name,
                'batch_code': reg.batch_team.batch_code,
                'preferred_position': reg.preferred_position,
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
    """Update match metadata, draft score, or status."""
    permission_classes = [IsTournamentManager]

    def patch(self, request, match_id):
        match = get_object_or_404(Match, pk=match_id)

        home_score = request.data.get('home_score')
        away_score = request.data.get('away_score')
        match_status = request.data.get('status')
        match_report = request.data.get('match_report')
        potm_id = request.data.get('player_of_the_match_id')

        if home_score is not None:
            match.home_score = int(home_score)
        if away_score is not None:
            match.away_score = int(away_score)
        if match_status:
            match.status = match_status
        if match_report is not None:
            match.match_report = match_report
        if potm_id:
            match.player_of_the_match = MemberProfile.objects.filter(pk=potm_id).first()

        match.updated_by = request.user
        match.save()

        return Response({
            'message': 'Match updated successfully.',
            'id': match.id,
            'home_score': match.home_score,
            'away_score': match.away_score,
            'status': match.status,
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

        # Validate team
        if int(team_id) not in (match.home_team_id, match.away_team_id):
            return Response({"error": "Selected team is not playing in this match."}, status=status.HTTP_400_BAD_REQUEST)

        team = match.home_team if int(team_id) == match.home_team_id else match.away_team

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

    def get(self, request, data_type):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="focus_cup_{data_type}.csv"'
        writer = csv.writer(response)

        if data_type == 'members':
            writer.writerow(['ID', 'Username', 'Email', 'Full Name', 'College', 'Department', 'Year', 'Fellowship Team', 'Gender', 'Eligible for Football', 'Followers'])
            for m in MemberProfile.objects.select_related('user').all():
                writer.writerow([
                    m.id, m.user.username, m.user.email, m.full_name,
                    m.get_college_display(), m.department, m.academic_year,
                    m.fellowship_team, m.gender, 'Yes' if m.is_football_eligible else 'No',
                    m.followers_count
                ])

        elif data_type == 'rosters':
            writer.writerow(['Registration ID', 'Batch Team', 'Player Name', 'Jersey Number', 'Position', 'Status'])
            for r in PlayerRegistration.objects.select_related('batch_team', 'member').all():
                writer.writerow([
                    r.id, r.batch_team.name, r.member.full_name,
                    r.jersey_number, r.preferred_position, r.status
                ])

        elif data_type == 'matches':
            writer.writerow(['Match ID', 'Date', 'Round', 'Home Team', 'Away Team', 'Home Score', 'Away Score', 'Status', 'Published'])
            for m in Match.objects.select_related('home_team', 'away_team').all():
                writer.writerow([
                    m.id, m.match_date, m.round_number, m.home_team.name,
                    m.away_team.name, m.home_score, m.away_score, m.status,
                    'Yes' if m.is_published else 'No'
                ])

        elif data_type == 'standings':
            writer.writerow(['Position', 'Batch', 'Played', 'Won', 'Drawn', 'Lost', 'Goals For', 'Goals Against', 'Goal Difference', 'Points'])
            standings = calculate_season_standings()
            for s in standings:
                writer.writerow([
                    s['position'], s['name'], s['played'], s['won'], s['drawn'],
                    s['lost'], s['goals_for'], s['goals_against'], s['goal_difference'], s['points']
                ])

        else:
            return Response({"error": "Invalid export type. Choose members, rosters, matches, or standings."}, status=status.HTTP_400_BAD_REQUEST)

        return response

"""
Authoritative Statistics & Standings Engine for AASTU Focus Football Cup.
All calculations derive from official, published, and completed match records.
"""

from collections import defaultdict
from django.db.models import Count, Q
from apps.competitions.models import Season, BatchTeam
from apps.matches.models import Match, MatchEvent, MatchSquad
from apps.members.models import MemberProfile


def get_active_season():
    """Returns the current active season, or the latest season created."""
    season = Season.objects.filter(is_active=True).first()
    if not season:
        season = Season.objects.first()
    return season


def calculate_season_standings(season_id=None):
    """
    Computes official league standings for the four competing batches:
    - 2nd Year
    - 3rd Year
    - 4th Year
    - 5th Year

    Rules:
    - Win = 3 pts
    - Draw = 1 pt
    - Loss = 0 pt
    - Played = Wins + Draws + Losses
    - Goal Difference = Goals For - Goals Against
    - Points = (Wins * 3) + Draws
    - Sorting: 1. Points, 2. Goal Difference, 3. Goals For, 4. Head-to-Head
    """
    if season_id:
        season = Season.objects.filter(pk=season_id).first()
    else:
        season = get_active_season()

    if not season:
        return []

    competing_teams = BatchTeam.objects.filter(is_competing=True).order_by('batch_code')
    
    # Initialize standings dictionary
    stats = {}
    for team in competing_teams:
        stats[team.id] = {
            'team_id': team.id,
            'batch_code': team.batch_code,
            'name': team.name,
            'nickname': team.nickname,
            'color_hex': team.color_hex,
            'played': 0,
            'won': 0,
            'drawn': 0,
            'lost': 0,
            'goals_for': 0,
            'goals_against': 0,
            'goal_difference': 0,
            'points': 0,
            'form': [],
            'head_to_head': defaultdict(lambda: {'pts': 0, 'gd': 0, 'gf': 0}),
        }

    # Fetch completed and published matches for this season
    matches = (
        Match.objects.filter(season=season, status='COMPLETED', is_published=True)
        .order_by('match_date', 'kick_off_time')
    )

    for match in matches:
        h_id = match.home_team_id
        a_id = match.away_team_id
        h_score = match.home_score
        a_score = match.away_score

        if h_id not in stats or a_id not in stats:
            continue

        # Home team stats
        stats[h_id]['played'] += 1
        stats[h_id]['goals_for'] += h_score
        stats[h_id]['goals_against'] += a_score

        # Away team stats
        stats[a_id]['played'] += 1
        stats[a_id]['goals_for'] += a_score
        stats[a_id]['goals_against'] += h_score

        if h_score > a_score:
            stats[h_id]['won'] += 1
            stats[h_id]['points'] += 3
            stats[h_id]['form'].append('W')

            stats[a_id]['lost'] += 1
            stats[a_id]['form'].append('L')

            stats[h_id]['head_to_head'][a_id]['pts'] += 3
            stats[h_id]['head_to_head'][a_id]['gd'] += (h_score - a_score)
            stats[h_id]['head_to_head'][a_id]['gf'] += h_score
            stats[a_id]['head_to_head'][h_id]['gd'] -= (h_score - a_score)
            stats[a_id]['head_to_head'][h_id]['gf'] += a_score

        elif h_score == a_score:
            stats[h_id]['drawn'] += 1
            stats[h_id]['points'] += 1
            stats[h_id]['form'].append('D')

            stats[a_id]['drawn'] += 1
            stats[a_id]['points'] += 1
            stats[a_id]['form'].append('D')

            stats[h_id]['head_to_head'][a_id]['pts'] += 1
            stats[a_id]['head_to_head'][h_id]['pts'] += 1
            stats[h_id]['head_to_head'][a_id]['gf'] += h_score
            stats[a_id]['head_to_head'][h_id]['gf'] += a_score

        else:
            stats[a_id]['won'] += 1
            stats[a_id]['points'] += 3
            stats[a_id]['form'].append('W')

            stats[h_id]['lost'] += 1
            stats[h_id]['form'].append('L')

            stats[a_id]['head_to_head'][h_id]['pts'] += 3
            stats[a_id]['head_to_head'][h_id]['gd'] += (a_score - h_score)
            stats[a_id]['head_to_head'][h_id]['gf'] += a_score
            stats[h_id]['head_to_head'][a_id]['gd'] -= (a_score - h_score)
            stats[h_id]['head_to_head'][a_id]['gf'] += h_score

    # Compute goal differences
    standings_list = []
    for team_id, row in stats.items():
        row['goal_difference'] = row['goals_for'] - row['goals_against']
        # Keep last 5 matches for form
        row['recent_form'] = row['form'][-5:]
        del row['head_to_head']  # Clean up before serialization
        standings_list.append(row)

    # Sort primarily by: points desc, goal_difference desc, goals_for desc, name asc
    standings_list.sort(
        key=lambda x: (
            -x['points'],
            -x['goal_difference'],
            -x['goals_for'],
            x['name']
        )
    )

    # Assign positions (1-indexed)
    for index, row in enumerate(standings_list, start=1):
        row['position'] = index

    return standings_list


def get_top_goalscorers(season_id=None, limit=10):
    """
    Calculates top scorers from official published matches.
    Excludes OWN_GOAL (own goals are not player goals).
    """
    season = Season.objects.filter(pk=season_id).first() if season_id else get_active_season()
    if not season:
        return []

    # Filter GOAL events from completed & published matches
    goal_events = (
        MatchEvent.objects.filter(
            match__season=season,
            match__status='COMPLETED',
            match__is_published=True,
            event_type='GOAL',
            player__isnull=False
        )
        .values('player')
        .annotate(total_goals=Count('id'))
        .order_by('-total_goals')[:limit]
    )

    player_ids = [item['player'] for item in goal_events]
    profiles = {p.id: p for p in MemberProfile.objects.filter(id__in=player_ids).select_related('user')}

    results = []
    for rank, item in enumerate(goal_events, start=1):
        prof = profiles.get(item['player'])
        if prof:
            results.append({
                'rank': rank,
                'player_id': prof.id,
                'username': prof.user.username,
                'full_name': prof.full_name,
                'batch': prof.get_competing_batch_display() or prof.academic_year,
                'department': prof.department,
                'position': prof.primary_position or "Forward",
                'jersey_number': prof.preferred_jersey_number,
                'profile_picture': prof.avatar_url,
                'avatar_url': prof.avatar_url,
                'profile_picture_url': prof.profile_picture_url,
                'goals': item['total_goals'],
            })

    return results


def get_top_assists(season_id=None, limit=10):
    """
    Calculates players with the most assists in published completed matches.
    """
    season = Season.objects.filter(pk=season_id).first() if season_id else get_active_season()
    if not season:
        return []

    # Either explicit ASSIST event or related_player on GOAL
    events = (
        MatchEvent.objects.filter(
            match__season=season,
            match__status='COMPLETED',
            match__is_published=True,
        )
        .filter(
            Q(event_type='ASSIST', player__isnull=False) |
            Q(event_type='GOAL', related_player__isnull=False)
        )
    )

    counts = defaultdict(int)
    for ev in events:
        if ev.event_type == 'ASSIST' and ev.player_id:
            counts[ev.player_id] += 1
        elif ev.event_type == 'GOAL' and ev.related_player_id:
            counts[ev.related_player_id] += 1

    sorted_assists = sorted(counts.items(), key=lambda x: -x[1])[:limit]
    player_ids = [x[0] for x in sorted_assists]
    profiles = {p.id: p for p in MemberProfile.objects.filter(id__in=player_ids).select_related('user')}

    results = []
    for rank, (p_id, total) in enumerate(sorted_assists, start=1):
        prof = profiles.get(p_id)
        if prof:
            results.append({
                'rank': rank,
                'player_id': prof.id,
                'username': prof.user.username,
                'full_name': prof.full_name,
                'batch': prof.get_competing_batch_display() or prof.academic_year,
                'department': prof.department,
                'position': prof.primary_position or "Midfielder",
                'profile_picture': prof.avatar_url,
                'avatar_url': prof.avatar_url,
                'profile_picture_url': prof.profile_picture_url,
                'assists': total,
            })

    return results


def get_most_followed_members(limit=10, batch_code=None):
    """
    Returns fellowship members with the highest follower counts.
    Can be filtered by batch.
    """
    qs = MemberProfile.objects.filter(is_approved=True, is_suspended=False)
    if batch_code:
        qs = qs.filter(competing_batch=batch_code)

    profiles = qs.select_related('user').order_by('-followers_count', 'first_name')[:limit]

    results = []
    for rank, p in enumerate(profiles, start=1):
        results.append({
            'rank': rank,
            'id': p.id,
            'username': p.user.username,
            'full_name': p.full_name,
            'batch': p.get_competing_batch_display() or p.academic_year,
            'college': p.get_college_display(),
            'department': p.department,
            'fellowship_team': p.fellowship_team,
            'followers_count': p.followers_count,
            'profile_picture': p.avatar_url,
            'avatar_url': p.avatar_url,
            'profile_picture_url': p.profile_picture_url,
            'personal_chant': p.personal_chant,
        })
    return results


def get_tournament_summary(season_id=None):
    """
    High-level KPIs for the homepage and manager dashboard.
    """
    season = Season.objects.filter(pk=season_id).first() if season_id else get_active_season()
    
    total_members = MemberProfile.objects.filter(is_approved=True).count()
    approved_players = MemberProfile.objects.filter(
        player_registrations__status='APPROVED'
    ).distinct().count()

    total_matches = Match.objects.filter(season=season).count() if season else 0
    completed_matches = Match.objects.filter(season=season, status='COMPLETED', is_published=True).count() if season else 0
    upcoming_matches = Match.objects.filter(season=season, status='SCHEDULED').count() if season else 0

    # Total goals in published matches
    total_goals = 0
    if season:
        goal_events = MatchEvent.objects.filter(
            match__season=season,
            match__status='COMPLETED',
            match__is_published=True,
            event_type__in=['GOAL', 'OWN_GOAL']
        ).count()
        total_goals = goal_events

    return {
        'total_members': total_members,
        'approved_players': approved_players,
        'total_matches': total_matches,
        'completed_matches': completed_matches,
        'upcoming_matches': upcoming_matches,
        'total_goals': total_goals,
    }

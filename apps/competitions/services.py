from datetime import timedelta
from itertools import combinations
from apps.competitions.models import Season, BatchTeam
from apps.matches.models import Match


def generate_round_robin_fixtures(season: Season, start_date=None, default_time=None, venue=None):
    """
    Generates a single round-robin fixture schedule for competing batch teams.
    For N teams: N * (N - 1) / 2 fixtures.
    For 4 teams: 6 fixtures total (each batch plays 3 matches).

    Prevents creating duplicate fixtures if teams have already been scheduled
    against each other in the same season.
    """
    competing_teams = list(BatchTeam.objects.filter(is_competing=True).order_by('batch_code'))
    if len(competing_teams) < 2:
        return 0, "At least 2 competing batch teams are required."

    match_date = start_date or season.start_date
    kick_off = default_time or "16:00"
    match_venue = venue or "AASTU Main Football Field"

    created_matches = []
    # Generate all unique pair combinations (Home, Away)
    pairs = list(combinations(competing_teams, 2))

    # Existing match pairings in this season
    existing_pairs = set()
    for m in Match.objects.filter(season=season):
        pair_key = tuple(sorted([m.home_team_id, m.away_team_id]))
        existing_pairs.add(pair_key)

    round_counter = 1
    current_date = match_date

    for idx, (team_a, team_b) in enumerate(pairs):
        pair_key = tuple(sorted([team_a.id, team_b.id]))
        if pair_key in existing_pairs:
            continue  # Avoid duplicate fixture

        # Alternate home and away
        home_team, away_team = (team_a, team_b) if idx % 2 == 0 else (team_b, team_a)

        match = Match.objects.create(
            season=season,
            round_number=round_counter,
            home_team=home_team,
            away_team=away_team,
            match_date=current_date,
            kick_off_time=kick_off,
            venue=match_venue,
            status='SCHEDULED',
            is_published=False,
        )
        created_matches.append(match)
        existing_pairs.add(pair_key)

        # Increment match date every 2 matches (e.g. weekend match days)
        if (idx + 1) % 2 == 0:
            round_counter += 1
            current_date += timedelta(days=7)

    return len(created_matches), f"Successfully generated {len(created_matches)} round-robin fixtures."

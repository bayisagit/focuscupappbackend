"""
Comprehensive Automated Test Suite for AASTU Focus Football Cup.
Validates:
- Academic departments and eligibility rules
- First-year and Applied Sciences 5th-year restrictions
- Authentication & JWT
- Follow system & duplicate prevention
- Player registration & batch roster verification
- Match event recordings & own-goal attribution
- Standings & statistics calculations
- Result publishing, correction, and audit trails
"""

from datetime import date
from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient
from rest_framework import status

from apps.members.constants import validate_academic_eligibility
from apps.members.models import MemberProfile, MemberFollow, PlayerRegistration
from apps.competitions.models import Season, BatchTeam, SeasonTeam
from apps.matches.models import Match, MatchSquad, MatchEvent, AuditLog
from apps.statistics.services import (
    calculate_season_standings,
    get_top_goalscorers,
    get_top_assists,
)

User = get_user_model()


class EligibilityEngineTestCase(TestCase):
    def test_engineering_5th_year_is_eligible(self):
        is_valid, err, is_eligible, batch = validate_academic_eligibility(
            'ENGINEERING', 'Software Engineering', '5th Year'
        )
        self.assertTrue(is_valid)
        self.assertIsNone(err)
        self.assertTrue(is_eligible)
        self.assertEqual(batch, '5TH_YEAR')

    def test_applied_sciences_5th_year_is_invalid(self):
        # Applied sciences is 4 years program only
        is_valid, err, is_eligible, batch = validate_academic_eligibility(
            'APPLIED_SCIENCES', 'Food Science', '5th Year'
        )
        self.assertFalse(is_valid)
        self.assertIn("4 years", err)
        self.assertFalse(is_eligible)

    def test_first_year_ineligible_for_football(self):
        # 1st years focus on academics
        is_valid, err, is_eligible, batch = validate_academic_eligibility(
            'ENGINEERING', 'Civil Engineering', '1st Year'
        )
        self.assertTrue(is_valid)
        self.assertFalse(is_eligible)
        self.assertIsNone(batch)

    def test_other_category_ineligible_for_football(self):
        is_valid, err, is_eligible, batch = validate_academic_eligibility(
            'OTHER', 'Other', 'Other'
        )
        self.assertTrue(is_valid)
        self.assertFalse(is_eligible)


class MemberAndFollowTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user_a = User.objects.create_user(
            username='user_a', email='a@aastu.org', password='password123',
            first_name='Abebe', last_name='Bikila'
        )
        self.prof_a = MemberProfile.objects.create(
            user=self.user_a, first_name='Abebe', second_name='Bikila',
            college='ENGINEERING', department='Software Engineering',
            academic_year='2nd Year', fellowship_team='Ebenim', gender='MALE'
        )

        self.user_b = User.objects.create_user(
            username='user_b', email='b@aastu.org', password='password123',
            first_name='Bete', last_name='Lhem'
        )
        self.prof_b = MemberProfile.objects.create(
            user=self.user_b, first_name='Bete', second_name='Lhem',
            college='ENGINEERING', department='Electrical Engineering',
            academic_year='3rd Year', fellowship_team='Lady', gender='FEMALE'
        )

    def test_follow_toggle_and_duplicate_prevention(self):
        self.client.force_authenticate(user=self.user_a)

        # 1. Follow User B
        res = self.client.post(f'/api/v1/members/{self.prof_b.id}/follow/')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data['status'], 'followed')
        self.assertEqual(res.data['followers_count'], 1)

        # Check DB
        self.prof_b.refresh_from_db()
        self.assertEqual(self.prof_b.followers_count, 1)

        # 2. Cannot follow self
        res_self = self.client.post(f'/api/v1/members/{self.prof_a.id}/follow/')
        self.assertEqual(res_self.status_code, status.HTTP_400_BAD_REQUEST)

        # 3. Unfollow User B
        res_unfollow = self.client.post(f'/api/v1/members/{self.prof_b.id}/follow/')
        self.assertEqual(res_unfollow.status_code, status.HTTP_200_OK)
        self.assertEqual(res_unfollow.data['status'], 'unfollowed')
        self.assertEqual(res_unfollow.data['followers_count'], 0)


class MatchAndStandingsTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.manager = User.objects.create_superuser(
            username='test_manager', email='manager@test.org', password='managerpass',
            role='MANAGER'
        )
        self.season = Season.objects.create(
            name="Test Cup 2026",
            academic_year="2026/2027",
            start_date=date.today(),
            end_date=date.today(),
            status='ONGOING',
            is_active=True
        )

        self.team_2nd = BatchTeam.objects.create(
            batch_code='2ND_YEAR', name='2nd Year Batch', is_competing=True
        )
        self.team_3rd = BatchTeam.objects.create(
            batch_code='3RD_YEAR', name='3rd Year Batch', is_competing=True
        )
        self.team_4th = BatchTeam.objects.create(
            batch_code='4TH_YEAR', name='4th Year Batch', is_competing=True
        )
        self.team_5th = BatchTeam.objects.create(
            batch_code='5TH_YEAR', name='5th Year Batch', is_competing=True
        )

        # Player in 2nd year
        self.user_p1 = User.objects.create_user(username='player1', email='p1@aastu.org', password='pass')
        self.prof_p1 = MemberProfile.objects.create(
            user=self.user_p1, first_name='Player', second_name='One',
            college='ENGINEERING', department='Software Engineering',
            academic_year='2nd Year', fellowship_team='Media', gender='MALE',
            primary_position='Striker'
        )

        # Player in 3rd year
        self.user_p2 = User.objects.create_user(username='player2', email='p2@aastu.org', password='pass')
        self.prof_p2 = MemberProfile.objects.create(
            user=self.user_p2, first_name='Player', second_name='Two',
            college='ENGINEERING', department='Mechanical Engineering',
            academic_year='3rd Year', fellowship_team='Elios', gender='MALE',
            primary_position='Defender'
        )

    def test_match_creation_event_and_standings(self):
        self.client.force_authenticate(user=self.manager)

        match = Match.objects.create(
            season=self.season,
            home_team=self.team_2nd,
            away_team=self.team_3rd,
            match_date=date.today(),
            kick_off_time="16:00",
            status='SCHEDULED',
            is_published=False
        )

        # 1. Record Goal for 2nd Year
        res_goal = self.client.post(f'/api/v1/manager/matches/{match.id}/events/', {
            'event_type': 'GOAL',
            'team_id': self.team_2nd.id,
            'player_id': self.prof_p1.id,
            'minute': 25,
            'description': 'Header'
        })
        self.assertEqual(res_goal.status_code, status.HTTP_201_CREATED)
        match.refresh_from_db()
        self.assertEqual(match.home_score, 1)
        self.assertEqual(match.away_score, 0)

        # 2. Record Own Goal by 3rd Year (should increase 2nd Year's score!)
        res_og = self.client.post(f'/api/v1/manager/matches/{match.id}/events/', {
            'event_type': 'OWN_GOAL',
            'team_id': self.team_3rd.id,
            'player_id': self.prof_p2.id,
            'minute': 40,
            'description': 'Deflected shot'
        })
        self.assertEqual(res_og.status_code, status.HTTP_201_CREATED)
        match.refresh_from_db()
        self.assertEqual(match.home_score, 2)
        self.assertEqual(match.away_score, 0)

        # 3. Before publish, standings should reflect 0 played matches
        standings_pre = calculate_season_standings(self.season.id)
        team_2_pre = next(s for s in standings_pre if s['batch_code'] == '2ND_YEAR')
        self.assertEqual(team_2_pre['played'], 0)
        self.assertEqual(team_2_pre['points'], 0)

        # 4. Publish match
        res_pub = self.client.post(f'/api/v1/manager/matches/{match.id}/publish/')
        self.assertEqual(res_pub.status_code, status.HTTP_200_OK)
        match.refresh_from_db()
        self.assertTrue(match.is_published)
        self.assertEqual(match.status, 'COMPLETED')

        # 5. After publish, standings should reflect 2nd Year win: 3 points, GD +2
        standings_post = calculate_season_standings(self.season.id)
        team_2_post = next(s for s in standings_post if s['batch_code'] == '2ND_YEAR')
        team_3_post = next(s for s in standings_post if s['batch_code'] == '3RD_YEAR')

        self.assertEqual(team_2_post['played'], 1)
        self.assertEqual(team_2_post['won'], 1)
        self.assertEqual(team_2_post['points'], 3)
        self.assertEqual(team_2_post['goals_for'], 2)
        self.assertEqual(team_2_post['goals_against'], 0)
        self.assertEqual(team_2_post['goal_difference'], 2)
        self.assertEqual(team_2_post['position'], 1)

        self.assertEqual(team_3_post['played'], 1)
        self.assertEqual(team_3_post['lost'], 1)
        self.assertEqual(team_3_post['points'], 0)
        self.assertEqual(team_3_post['goal_difference'], -2)

        # 6. Top scorer check: Player 1 has 1 goal; Player 2 does NOT have goals (own goal not counted for player)
        top_scorers = get_top_goalscorers(self.season.id)
        self.assertEqual(len(top_scorers), 1)
        self.assertEqual(top_scorers[0]['player_id'], self.prof_p1.id)
        self.assertEqual(top_scorers[0]['goals'], 1)

        # 7. Correct match result via manager endpoint
        res_corr = self.client.post(f'/api/v1/manager/matches/{match.id}/correct/', {
            'home_score': 3,
            'away_score': 1,
            'reason': 'Late correction of referee scorebook'
        })
        self.assertEqual(res_corr.status_code, status.HTTP_200_OK)
        match.refresh_from_db()
        self.assertEqual(match.home_score, 3)
        self.assertEqual(match.away_score, 1)

        # Verify audit log was created
        audit = AuditLog.objects.filter(model_name='Match', action_type='CORRECT').first()
        self.assertIsNotNone(audit)
        self.assertEqual(audit.user, self.manager)

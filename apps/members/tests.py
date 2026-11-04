from django.test import TestCase
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework import status
from datetime import timedelta
from apps.members.models import MemberProfile, PlayerRegistration
from apps.competitions.models import Season, BatchTeam

User = get_user_model()


class BatchJerseyUniquenessTestCase(TestCase):
    def setUp(self):
        self.client = APIClient()

        # Create active season
        today = timezone.now().date()
        self.season = Season.objects.create(
            name="Focus Cup 2026",
            academic_year="2026/2027",
            start_date=today,
            end_date=today + timedelta(days=90),
            is_active=True
        )

        # Create batch teams
        self.batch_2nd = BatchTeam.objects.create(
            name="2nd Year Batch",
            batch_code="2ND_YEAR"
        )
        self.batch_3rd = BatchTeam.objects.create(
            name="3rd Year Batch",
            batch_code="3RD_YEAR"
        )

        # Create member 1 (2nd year)
        self.user1 = User.objects.create_user(username="player1", email="p1@example.com", password="pass")
        self.profile1 = MemberProfile.objects.create(
            user=self.user1,
            first_name="Bereket",
            second_name="Tesfaye",
            college="ENGINEERING",
            department="SOFTWARE",
            academic_year="2nd Year",
            competing_batch="2ND_YEAR",
            is_football_eligible=True,
            is_approved=True
        )

        # Create member 2 (2nd year, same batch)
        self.user2 = User.objects.create_user(username="player2", email="p2@example.com", password="pass")
        self.profile2 = MemberProfile.objects.create(
            user=self.user2,
            first_name="Nahom",
            second_name="Alemu",
            college="ENGINEERING",
            department="CIVIL",
            academic_year="2nd Year",
            competing_batch="2ND_YEAR",
            is_football_eligible=True,
            is_approved=True
        )

        # Create member 3 (3rd year, different batch)
        self.user3 = User.objects.create_user(username="player3", email="p3@example.com", password="pass")
        self.profile3 = MemberProfile.objects.create(
            user=self.user3,
            first_name="Dawit",
            second_name="Mengesha",
            college="ENGINEERING",
            department="MECHANICAL",
            academic_year="3rd Year",
            competing_batch="3RD_YEAR",
            is_football_eligible=True,
            is_approved=True
        )

    def test_apply_available_jersey_success(self):
        """Player 1 successfully registers with jersey #10."""
        self.client.force_authenticate(user=self.user1)
        res = self.client.post('/api/v1/members/apply-player/', {
            'jersey_number': 10,
            'preferred_position': 'Striker'
        }, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        reg = PlayerRegistration.objects.get(member=self.profile1)
        self.assertEqual(reg.jersey_number, 10)
        self.assertEqual(reg.status, 'PENDING')

    def test_apply_taken_jersey_in_same_batch_fails(self):
        """Player 2 cannot register with jersey #10 because Player 1 already claimed it in the same batch."""
        # Player 1 registers with #10
        PlayerRegistration.objects.create(
            member=self.profile1,
            season=self.season,
            batch_team=self.batch_2nd,
            jersey_number=10,
            preferred_position='Striker',
            status='PENDING'
        )

        # Player 2 attempts to register with #10 in the same batch
        self.client.force_authenticate(user=self.user2)
        res = self.client.post('/api/v1/members/apply-player/', {
            'jersey_number': 10,
            'preferred_position': 'Midfielder'
        }, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already taken in 2nd Year Batch", res.data.get('error', ''))
        self.assertEqual(res.data.get('code'), 'JERSEY_TAKEN')
        self.assertEqual(res.data.get('jersey_number'), 10)

    def test_different_batch_can_use_same_jersey_number(self):
        """Player 3 in 3rd Year Batch CAN register with jersey #10 even though 2nd Year has #10."""
        # 2nd Year has #10
        PlayerRegistration.objects.create(
            member=self.profile1,
            season=self.season,
            batch_team=self.batch_2nd,
            jersey_number=10,
            preferred_position='Striker',
            status='APPROVED'
        )

        # 3rd Year applies for #10
        self.client.force_authenticate(user=self.user3)
        res = self.client.post('/api/v1/members/apply-player/', {
            'jersey_number': 10,
            'preferred_position': 'Winger'
        }, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        reg = PlayerRegistration.objects.get(member=self.profile3)
        self.assertEqual(reg.jersey_number, 10)
        self.assertEqual(reg.batch_team, self.batch_3rd)

    def test_batch_jerseys_api_endpoint(self):
        """Endpoint /api/v1/members/batch-jerseys/ returns taken numbers accurately."""
        PlayerRegistration.objects.create(
            member=self.profile1,
            season=self.season,
            batch_team=self.batch_2nd,
            jersey_number=7,
            preferred_position='Midfielder',
            status='APPROVED'
        )

        res = self.client.get('/api/v1/members/batch-jerseys/?batch_code=2ND_YEAR')
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn(7, res.data.get('taken_numbers', []))

        # Check that 3rd year endpoint does not show 7 as taken
        res_3rd = self.client.get('/api/v1/members/batch-jerseys/?batch_code=3RD_YEAR')
        self.assertEqual(res_3rd.status_code, status.HTTP_200_OK)
        self.assertNotIn(7, res_3rd.data.get('taken_numbers', []))

    def test_model_clean_validation(self):
        """PlayerRegistration.clean() raises ValidationError on duplicate jersey in the same batch."""
        PlayerRegistration.objects.create(
            member=self.profile1,
            season=self.season,
            batch_team=self.batch_2nd,
            jersey_number=9,
            preferred_position='Striker',
            status='APPROVED'
        )

        duplicate_reg = PlayerRegistration(
            member=self.profile2,
            season=self.season,
            batch_team=self.batch_2nd,
            jersey_number=9,
            preferred_position='Winger',
            status='PENDING'
        )
        with self.assertRaises(ValidationError):
            duplicate_reg.clean()

    def test_reapply_after_rejection_with_different_jersey(self):
        """A rejected player can resubmit their application with an available jersey number."""
        reg = PlayerRegistration.objects.create(
            member=self.profile1,
            season=self.season,
            batch_team=self.batch_2nd,
            jersey_number=10,
            preferred_position='Striker',
            status='REJECTED',
            rejection_reason='Duplicate preferred number'
        )

        self.client.force_authenticate(user=self.user1)
        res = self.client.post('/api/v1/members/apply-player/', {
            'jersey_number': 19,
            'preferred_position': 'Striker'
        }, format='json')

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        reg.refresh_from_db()
        self.assertEqual(reg.jersey_number, 19)
        self.assertEqual(reg.status, 'PENDING')
        self.assertEqual(reg.rejection_reason, '')

    def test_manager_cannot_approve_duplicate_jersey(self):
        """Manager cannot approve an application if another player in that batch is already approved with that jersey."""
        manager_user = User.objects.create_user(
            username="manager1",
            email="m@test.com",
            password="pass",
            role="MANAGER",
            is_staff=True
        )

        # Approved player with #10
        PlayerRegistration.objects.create(
            member=self.profile1,
            season=self.season,
            batch_team=self.batch_2nd,
            jersey_number=10,
            preferred_position='Striker',
            status='APPROVED'
        )

        # Pending player with #10
        reg2 = PlayerRegistration.objects.create(
            member=self.profile2,
            season=self.season,
            batch_team=self.batch_2nd,
            jersey_number=10,
            preferred_position='Midfielder',
            status='PENDING'
        )

        self.client.force_authenticate(user=manager_user)
        res = self.client.post(f'/api/v1/manager/player-registrations/{reg2.id}/review/', {
            'status': 'APPROVED'
        }, format='json')

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("already assigned", res.data.get('error', ''))
        reg2.refresh_from_db()
        self.assertEqual(reg2.status, 'PENDING')


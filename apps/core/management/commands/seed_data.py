"""
Management command to seed initial tournament data, batch teams,
manager account, members, fixtures, and events for Focus Football Cup.
"""

from datetime import date, timedelta
from django.core.management.base import BaseCommand
from django.db import transaction
from apps.accounts.models import CustomUser
from apps.members.models import MemberProfile, MemberFollow, PlayerRegistration
from apps.competitions.models import Season, BatchTeam, SeasonTeam
from apps.matches.models import Match, MatchSquad, MatchEvent, AuditLog
from apps.statistics.models import TournamentAward
from apps.community.models import Announcement, GalleryAlbum, GalleryPhoto
from apps.core.models import SiteSetting
from apps.competitions.services import generate_round_robin_fixtures


class Command(BaseCommand):
    help = "Seeds initial database for Focus Football Cup"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("Seeding Focus Football Cup initial data..."))

        with transaction.atomic():
            # 1. Site Setting
            site_setting, _ = SiteSetting.objects.get_or_create(id=1)
            site_setting.site_title = "AASTU Focus Fellowship – Focus Football Cup"
            site_setting.tagline = "Winning is a bonus; friendship, joy, and fellowship come first!"
            site_setting.verse_text = "Behold, how good and how pleasant it is for brethren to dwell together in unity!"
            site_setting.verse_reference = "Psalm 133:1"
            site_setting.facebook_url = "https://web.facebook.com/fstufocus"
            site_setting.telegram_url = "https://t.me/fstufocus"
            site_setting.tiktok_url = "https://www.tiktok.com/@aastu_focus?lang=en"
            site_setting.instagram_url = "https://www.instagram.com/aastufocus/"
            site_setting.youtube_url = "https://www.youtube.com/@aastufocusofficial9025"
            site_setting.contact_phone = "+25191 784 1282"
            site_setting.save()

            # 2. Superuser / Manager
            manager_user, created = CustomUser.objects.get_or_create(
                username='manager',
                defaults={
                    'email': 'manager@aastufocus.org',
                    'first_name': 'Tournament',
                    'last_name': 'Director',
                    'role': 'MANAGER',
                    'is_staff': True,
                    'is_superuser': True,
                }
            )
            if created:
                manager_user.set_password('focuscup2026')
                manager_user.save()
                self.stdout.write(self.style.SUCCESS("Created Manager user: manager / focuscup2026"))

            # Manager profile
            MemberProfile.objects.get_or_create(
                user=manager_user,
                defaults={
                    'first_name': 'Tournament',
                    'second_name': 'Director',
                    'college': 'ENGINEERING',
                    'department': 'Software Engineering',
                    'academic_year': '5th Year',
                    'fellowship_team': 'Media',
                    'gender': 'MALE',
                    'personal_chant': 'Christ Above Everything',
                    'is_football_eligible': True,
                    'competing_batch': '5TH_YEAR',
                }
            )

            # 3. Batch Teams (4 Competing + 1 Other)
            teams_data = [
                {
                    'batch_code': '2ND_YEAR',
                    'name': '2nd Year Batch',
                    'nickname': 'The Conquerors',
                    'color_hex': '#10B981',
                    'motto': 'United in Youth and Faith',
                    'description': 'Energetic, passionate, and full of fellowship joy. Building brotherhood across campuses.',
                    'is_competing': True,
                },
                {
                    'batch_code': '3RD_YEAR',
                    'name': '3rd Year Batch',
                    'nickname': 'The Light Bearers',
                    'color_hex': '#3B82F6',
                    'motto': 'Walking as Children of Light',
                    'description': 'Balanced tacticians with deep camaraderie and high fellowship spirit.',
                    'is_competing': True,
                },
                {
                    'batch_code': '4TH_YEAR',
                    'name': '4th Year Batch',
                    'nickname': 'The Shepherds',
                    'color_hex': '#8B5CF6',
                    'motto': 'Guiding with Love and Grace',
                    'description': 'Experienced and resilient, demonstrating Christ-like humility on and off the pitch.',
                    'is_competing': True,
                },
                {
                    'batch_code': '5TH_YEAR',
                    'name': '5th Year Batch',
                    'nickname': 'The Pillars',
                    'color_hex': '#F59E0B',
                    'motto': 'Finishing the Race with Glory',
                    'description': 'Graduating engineering batch, playing with maturity, honor, and heartfelt fellowship.',
                    'is_competing': True,
                },
                {
                    'batch_code': 'OTHER',
                    'name': 'Other Fellowship Members',
                    'nickname': 'The Family in Christ',
                    'color_hex': '#64748B',
                    'motto': 'One Body, Many Members',
                    'description': 'Community-only fellowship members (alumni, 1st years, guests) cheering on their brethren.',
                    'is_competing': False,
                },
            ]

            batch_teams = {}
            for t in teams_data:
                team_obj, _ = BatchTeam.objects.get_or_create(
                    batch_code=t['batch_code'],
                    defaults=t
                )
                batch_teams[t['batch_code']] = team_obj

            # 4. Season
            today = date.today()
            season, _ = Season.objects.get_or_create(
                name="Focus Football Cup - Semester I 2026/27",
                defaults={
                    'academic_year': '2026/2027',
                    'semester': 'Semester 1',
                    'start_date': today - timedelta(days=14),
                    'end_date': today + timedelta(days=28),
                    'registration_start': today - timedelta(days=30),
                    'registration_end': today - timedelta(days=15),
                    'status': 'ONGOING',
                    'is_active': True,
                    'rules': (
                        "AASTU Focus Fellowship Tournament Rules:\n"
                        "1. Win: 3 points, Draw: 1 point, Loss: 0 points.\n"
                        "2. Central Motto: 'Winning is a bonus; friendship, joy, and fellowship come first!'\n"
                        "3. Single round-robin without second legs."
                    )
                }
            )

            for team in batch_teams.values():
                if team.is_competing:
                    SeasonTeam.objects.get_or_create(season=season, batch_team=team)

            # 5. Fellowship Members (Diverse batch & department mix)
            sample_members = [
                # 2nd Year Players
                ('yonatan_k', 'Yonatan', 'Kassahun', 'ENGINEERING', 'Software Engineering', '2nd Year', 'Ebenim', 'MALE', 'Striker', 9, 'Jesus Is My Savior', '2ND_YEAR'),
                ('biruk_t', 'Biruk', 'Tadesse', 'ENGINEERING', 'Electrical Engineering', '2nd Year', 'Media', 'MALE', 'Goalkeeper', 1, 'In His Hands', '2ND_YEAR'),
                ('marcos_g', 'Marcos', 'Getachew', 'APPLIED_SCIENCES', 'Biotechnology', '2nd Year', 'BS Team', 'MALE', 'Midfielder', 8, 'Playing for His Glory', '2ND_YEAR'),
                ('selam_a', 'Selam', 'Alemu', 'ENGINEERING', 'Architecture', '2nd Year', 'Lady', 'FEMALE', 'Winger', 11, 'Joyful in Hope', '2ND_YEAR'),

                # 3rd Year Players
                ('samuel_b', 'Samuel', 'Bekele', 'ENGINEERING', 'Mechanical Engineering', '3rd Year', 'Elios', 'MALE', 'Midfielder', 10, 'Christ Above Everything', '3RD_YEAR'),
                ('dawit_m', 'Dawit', 'Mengesha', 'ENGINEERING', 'Civil Engineering', '3rd Year', 'Action and Prayer', 'MALE', 'Defender', 4, 'Rock of Ages', '3RD_YEAR'),
                ('natnael_s', 'Natnael', 'Shiferaw', 'APPLIED_SCIENCES', 'Food Science', '3rd Year', 'Ebenim', 'MALE', 'Striker', 7, 'One Team, One Family', '3RD_YEAR'),
                ('martha_h', 'Martha', 'Haile', 'APPLIED_SCIENCES', 'Geology', '3rd Year', 'Lady', 'FEMALE', 'Full Back', 3, 'Faithful and True', '3RD_YEAR'),

                # 4th Year Players
                ('bereket_w', 'Bereket', 'Wolde', 'ENGINEERING', 'Electromechanical Engineering', '4th Year', 'BS Team', 'MALE', 'Attacking Midfielder', 14, 'Grace and Peace', '4TH_YEAR'),
                ('yohannes_d', 'Yohannes', 'Daniel', 'ENGINEERING', 'Chemical Engineering', '4th Year', 'Ebenim', 'MALE', 'Goalkeeper', 12, 'Shield of Faith', '4TH_YEAR'),
                ('caleb_t', 'Caleb', 'Teklu', 'APPLIED_SCIENCES', 'Industrial Engineering', '4th Year', 'Media', 'MALE', 'Centre Back', 5, 'Standing Firm in Christ', '4TH_YEAR'),
                ('helen_g', 'Helen', 'Girma', 'ENGINEERING', 'Environmental Engineering', '4th Year', 'Action and Prayer', 'FEMALE', 'Midfielder', 6, 'Light of the World', '4TH_YEAR'),

                # 5th Year Players (Engineering Only!)
                ('ezra_a', 'Ezra', 'Assefa', 'ENGINEERING', 'Software Engineering', '5th Year', 'Ebenim', 'MALE', 'Striker', 11, 'Finishing Strong in Grace', '5TH_YEAR'),
                ('mulugeta_b', 'Mulugeta', 'Beyene', 'ENGINEERING', 'Mining Engineering', '5th Year', 'Elios', 'MALE', 'Midfielder', 8, 'Humble in Victory', '5TH_YEAR'),
                ('yared_k', 'Yared', 'Kebede', 'ENGINEERING', 'Civil Engineering', '5th Year', 'Ebenim', 'MALE', 'Defender', 2, 'Pillar of Truth', '5TH_YEAR'),

                # Community-only member: 1st Year (Concentrating on academics!)
                ('abel_f', 'Abel', 'Fikre', 'ENGINEERING', 'Civil Engineering', '1st Year', 'BS Team', 'MALE', 'Other', None, 'Studying Diligently in Christ', None),
                # Community-only member: Other category
                ('dr_solomon', 'Solomon', 'Worku', 'OTHER', 'Other', 'Other', 'Action and Prayer', 'MALE', 'Other', None, 'Guiding the Next Generation', 'OTHER'),
            ]

            created_profiles = {}
            for u_name, f_name, l_name, col, dept, yr, team_fellowship, gen, pos, num, chant, comp_batch in sample_members:
                user, u_created = CustomUser.objects.get_or_create(
                    username=u_name,
                    defaults={
                        'email': f"{u_name}@aastufocus.org",
                        'first_name': f_name,
                        'last_name': l_name,
                        'role': 'MEMBER',
                    }
                )
                if u_created:
                    user.set_password('fellowship2026')
                    user.save()

                prof, p_created = MemberProfile.objects.get_or_create(
                    user=user,
                    defaults={
                        'first_name': f_name,
                        'second_name': l_name,
                        'college': col,
                        'department': dept,
                        'academic_year': yr,
                        'fellowship_team': team_fellowship,
                        'gender': gen,
                        'primary_position': pos,
                        'preferred_jersey_number': num,
                        'personal_chant': chant,
                        'followers_count': 0,
                    }
                )
                created_profiles[u_name] = prof

                # If eligible, create approved PlayerRegistration
                if prof.is_football_eligible and prof.competing_batch in batch_teams:
                    team_obj = batch_teams[prof.competing_batch]
                    PlayerRegistration.objects.get_or_create(
                        member=prof,
                        season=season,
                        defaults={
                            'batch_team': team_obj,
                            'preferred_position': pos or 'Midfielder',
                            'jersey_number': num or 10,
                            'status': 'APPROVED',
                            'reviewed_by': manager_user,
                            'reviewed_at': today - timedelta(days=16),
                        }
                    )

            # 6. Establish Following Relationships
            follows = [
                ('yonatan_k', 'samuel_b'),
                ('yonatan_k', 'bereket_w'),
                ('biruk_t', 'yonatan_k'),
                ('samuel_b', 'ezra_a'),
                ('samuel_b', 'yonatan_k'),
                ('bereket_w', 'samuel_b'),
                ('natnael_s', 'samuel_b'),
                ('ezra_a', 'yonatan_k'),
                ('ezra_a', 'samuel_b'),
                ('ezra_a', 'bereket_w'),
                ('abel_f', 'samuel_b'),
                ('abel_f', 'ezra_a'),
            ]
            for follower_u, following_u in follows:
                f_user = CustomUser.objects.get(username=follower_u)
                target_user = CustomUser.objects.get(username=following_u)
                if not MemberFollow.objects.filter(follower=f_user, following=target_user).exists():
                    MemberFollow.objects.create(follower=f_user, following=target_user)
                    MemberProfile.objects.filter(user=target_user).update(followers_count=MemberProfile.objects.get(user=target_user).followers_count + 1)
                    MemberProfile.objects.filter(user=f_user).update(following_count=MemberProfile.objects.get(user=f_user).following_count + 1)

            # 7. Generate Fixtures (6 single-round-robin matches)
            generate_round_robin_fixtures(season=season, start_date=today - timedelta(days=10))

            # 8. Record Results for 2 Completed Matches
            matches = list(Match.objects.filter(season=season).order_by('match_date', 'kick_off_time'))
            if len(matches) >= 2:
                # Match 1: 2nd Year vs 3rd Year (Completed: 2nd Year 2 - 1 3rd Year)
                m1 = matches[0]
                m1.status = 'COMPLETED'
                m1.is_published = True
                m1.home_score = 2
                m1.away_score = 1
                m1.match_report = (
                    "A vibrant, high-energy clash opened the tournament! 2nd Year Warriors seized the lead early, "
                    "with Yonatan Kassahun displaying clinical finishing. Samuel Bekele equalized for 3rd Year "
                    "before Marcos Getachew clinched victory with a brilliant strike in the 74th minute. "
                    "Both batches knelt in joint prayer at full time, thanking God for fellowship."
                )
                m1.player_of_the_match = created_profiles.get('yonatan_k')
                m1.save()

                # Squads for m1
                squad_players_m1 = [
                    (m1.home_team, 'biruk_t', 1, True, True),
                    (m1.home_team, 'yonatan_k', 9, True, False),
                    (m1.home_team, 'marcos_g', 8, True, False),
                    (m1.away_team, 'samuel_b', 10, True, False),
                    (m1.away_team, 'dawit_m', 4, True, False),
                    (m1.away_team, 'natnael_s', 7, True, False),
                ]
                for team_obj, p_uname, j_num, is_start, is_gk in squad_players_m1:
                    p_prof = created_profiles.get(p_uname)
                    if p_prof:
                        MatchSquad.objects.get_or_create(
                            match=m1, player=p_prof,
                            defaults={'team': team_obj, 'jersey_number': j_num, 'is_starter': is_start, 'is_goalkeeper': is_gk}
                        )

                # Events for m1
                MatchEvent.objects.get_or_create(
                    match=m1, minute=18, event_type='GOAL',
                    defaults={'team': m1.home_team, 'player': created_profiles.get('yonatan_k'), 'description': 'Low driven shot past the keeper!'}
                )
                MatchEvent.objects.get_or_create(
                    match=m1, minute=52, event_type='GOAL',
                    defaults={'team': m1.away_team, 'player': created_profiles.get('samuel_b'), 'description': 'Curled free-kick into top corner!'}
                )
                MatchEvent.objects.get_or_create(
                    match=m1, minute=74, event_type='GOAL',
                    defaults={'team': m1.home_team, 'player': created_profiles.get('marcos_g'), 'related_player': created_profiles.get('yonatan_k'), 'description': 'Fine volley assisted by Yonatan!'}
                )
                MatchEvent.objects.get_or_create(
                    match=m1, minute=82, event_type='YELLOW_CARD',
                    defaults={'team': m1.away_team, 'player': created_profiles.get('dawit_m'), 'description': 'Tactical foul near midfield.'}
                )

                # Match 2: 4th Year vs 5th Year (Completed: 4th Year 1 - 3 5th Year)
                m2 = matches[1]
                m2.status = 'COMPLETED'
                m2.is_published = True
                m2.home_score = 1
                m2.away_score = 3
                m2.match_report = (
                    "The veteran 5th Year Pillars showcased masterclass teamwork. Ezra Assefa netted a brace, "
                    "leading his batch to victory. Bereket Wolde provided a sublime strike for 4th Year. "
                    "Warm embraces and songs of praise crowned the end of the match."
                )
                m2.player_of_the_match = created_profiles.get('ezra_a')
                m2.save()

                squad_players_m2 = [
                    (m2.home_team, 'yohannes_d', 12, True, True),
                    (m2.home_team, 'bereket_w', 14, True, False),
                    (m2.home_team, 'caleb_t', 5, True, False),
                    (m2.away_team, 'ezra_a', 11, True, False),
                    (m2.away_team, 'mulugeta_b', 8, True, False),
                    (m2.away_team, 'yared_k', 2, True, False),
                ]
                for team_obj, p_uname, j_num, is_start, is_gk in squad_players_m2:
                    p_prof = created_profiles.get(p_uname)
                    if p_prof:
                        MatchSquad.objects.get_or_create(
                            match=m2, player=p_prof,
                            defaults={'team': team_obj, 'jersey_number': j_num, 'is_starter': is_start, 'is_goalkeeper': is_gk}
                        )

                MatchEvent.objects.get_or_create(
                    match=m2, minute=12, event_type='GOAL',
                    defaults={'team': m2.away_team, 'player': created_profiles.get('ezra_a'), 'description': 'Powerful header off a corner kick!'}
                )
                MatchEvent.objects.get_or_create(
                    match=m2, minute=34, event_type='GOAL',
                    defaults={'team': m2.home_team, 'player': created_profiles.get('bereket_w'), 'description': 'Clinical finish from 20 yards.'}
                )
                MatchEvent.objects.get_or_create(
                    match=m2, minute=65, event_type='GOAL',
                    defaults={'team': m2.away_team, 'player': created_profiles.get('ezra_a'), 'related_player': created_profiles.get('mulugeta_b'), 'description': 'Second goal of the match for Ezra!'}
                )
                MatchEvent.objects.get_or_create(
                    match=m2, minute=88, event_type='GOAL',
                    defaults={'team': m2.away_team, 'player': created_profiles.get('mulugeta_b'), 'description': 'Sealed the victory with late strike.'}
                )

                # Set match 3 as scheduled for this Saturday
                if len(matches) >= 3:
                    m3 = matches[2]
                    m3.match_date = today + timedelta(days=2)
                    m3.status = 'SCHEDULED'
                    m3.save()

            # 9. Announcements
            announcements = [
                (
                    "Welcome to AASTU Focus Football Cup 2026/27!",
                    "TOURNAMENT",
                    "IMPORTANT",
                    "Praise God! We are excited to officially kick off our semester tournament. "
                    "Remember our foundational truth: 'Winning is a bonus; friendship, joy, and fellowship come first!' "
                    "All fellowship members are invited to come support their brothers and sisters.",
                    True
                ),
                (
                    "Upcoming Match Day Schedule: 2nd Year vs 4th Year",
                    "MATCH_DAY",
                    "NORMAL",
                    "This Saturday at 4:00 PM at AASTU Main Football Field. "
                    "Come early for fellowship prayer and praise songs before kick-off!",
                    False
                ),
                (
                    "Fellowship Prayer & Praise Night",
                    "FELLOWSHIP",
                    "NORMAL",
                    "Join us this Friday evening for our weekly praise, thanksgiving, and prayer session. "
                    "Let us commit all teams and our campus fellowship into the hands of our Lord.",
                    False
                ),
            ]
            for title, cat, prio, content, pinned in announcements:
                Announcement.objects.get_or_create(
                    title=title,
                    defaults={
                        'category': cat,
                        'priority': prio,
                        'content': content,
                        'is_pinned': pinned,
                        'author': manager_user,
                    }
                )

            # 10. Gallery Albums
            album, _ = GalleryAlbum.objects.get_or_create(
                title="Focus Cup Opening Match Highlights",
                defaults={
                    'description': "Joyful moments, prayers, and competitive action from our opening match fixtures."
                }
            )

            # 11. Tournament Awards (Preview / Sample)
            TournamentAward.objects.get_or_create(
                season=season,
                category='FELLOWSHIP_SPIRIT',
                defaults={
                    'title': 'Fellowship Spirit Award - Week 1',
                    'recipient_member': created_profiles.get('samuel_b'),
                    'citation': 'Recognized for exemplary humility, uplifting opposing players, and leading post-match fellowship prayers.',
                }
            )

        self.stdout.write(self.style.SUCCESS("Focus Football Cup seeded successfully!"))

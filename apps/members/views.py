from rest_framework import status, permissions, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, F
from django.shortcuts import get_object_or_404
from django.http import Http404
from django.contrib.auth import get_user_model
from apps.members.models import MemberProfile, MemberFollow, PlayerRegistration
from apps.members.serializers import (
    MemberProfileListSerializer,
    MemberProfileDetailSerializer,
    MemberProfileUpdateSerializer,
    PlayerRegistrationSerializer,
)
from apps.members.constants import (
    COLLEGE_CHOICES,
    ENGINEERING_DEPARTMENTS,
    APPLIED_SCIENCES_DEPARTMENTS,
    OTHER_DEPARTMENTS,
    ENGINEERING_YEARS,
    APPLIED_SCIENCES_YEARS,
    OTHER_YEARS,
    FELLOWSHIP_TEAMS,
    GENDER_CHOICES,
    FOOTBALL_POSITIONS,
    COMPETING_BATCH_CHOICES,
)
from apps.competitions.models import Season, BatchTeam
from apps.community.models import Notification

User = get_user_model()


class AcademicOptionsAPIView(APIView):
    """Returns dynamic options for registration and filters."""
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        return Response({
            'colleges': [{'value': k, 'label': v} for k, v in COLLEGE_CHOICES],
            'departments': {
                'ENGINEERING': [{'value': k, 'label': v} for k, v in ENGINEERING_DEPARTMENTS],
                'APPLIED_SCIENCES': [{'value': k, 'label': v} for k, v in APPLIED_SCIENCES_DEPARTMENTS],
                'OTHER': [{'value': k, 'label': v} for k, v in OTHER_DEPARTMENTS],
            },
            'academic_years': {
                'ENGINEERING': [{'value': k, 'label': v} for k, v in ENGINEERING_YEARS],
                'APPLIED_SCIENCES': [{'value': k, 'label': v} for k, v in APPLIED_SCIENCES_YEARS],
                'OTHER': [{'value': k, 'label': v} for k, v in OTHER_YEARS],
            },
            'fellowship_teams': [{'value': k, 'label': v} for k, v in FELLOWSHIP_TEAMS],
            'genders': [{'value': k, 'label': v} for k, v in GENDER_CHOICES],
            'football_positions': [{'value': k, 'label': v} for k, v in FOOTBALL_POSITIONS],
            'competing_batches': [{'value': k, 'label': v} for k, v in COMPETING_BATCH_CHOICES],
        })


class MemberListAPIView(generics.ListAPIView):
    """Searchable & filterable directory of fellowship members."""
    serializer_class = MemberProfileListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        qs = (
            MemberProfile.objects.filter(is_approved=True, is_suspended=False)
            .select_related('user')
        )
        search = self.request.query_params.get('search')
        if search:
            qs = qs.filter(
                Q(first_name__icontains=search) |
                Q(second_name__icontains=search) |
                Q(user__username__icontains=search) |
                Q(personal_chant__icontains=search) |
                Q(department__icontains=search)
            )

        batch = self.request.query_params.get('batch')
        if batch:
            if batch == 'OTHER':
                qs = qs.filter(Q(competing_batch='OTHER') | Q(academic_year='Other'))
            else:
                qs = qs.filter(competing_batch=batch)

        college = self.request.query_params.get('college')
        if college:
            qs = qs.filter(college=college)

        department = self.request.query_params.get('department')
        if department:
            qs = qs.filter(department=department)

        fellowship_team = self.request.query_params.get('fellowship_team')
        if fellowship_team:
            qs = qs.filter(fellowship_team=fellowship_team)

        gender = self.request.query_params.get('gender')
        if gender:
            qs = qs.filter(gender=gender)

        position = self.request.query_params.get('position')
        if position:
            qs = qs.filter(primary_position=position)

        eligible_only = self.request.query_params.get('eligible_only')
        if eligible_only in ('true', '1'):
            qs = qs.filter(is_football_eligible=True)

        sort_by = self.request.query_params.get('sort_by', 'followers')
        if sort_by == 'name':
            qs = qs.order_by('first_name', 'second_name')
        elif sort_by == 'newest':
            qs = qs.order_by('-created_at')
        else:
            qs = qs.order_by('-followers_count', 'first_name')

        return qs


class MemberDetailAPIView(APIView):
    """Detailed member profile by username or id."""
    permission_classes = [permissions.AllowAny]

    def get(self, request, identifier):
        import urllib.parse
        clean_identifier = urllib.parse.unquote(str(identifier)).strip()

        if clean_identifier.isdigit():
            profile = get_object_or_404(
                MemberProfile.objects.select_related('user'),
                id=int(clean_identifier),
                is_suspended=False
            )
        else:
            profile = (
                MemberProfile.objects.select_related('user').filter(
                    Q(user__username=clean_identifier) |
                    Q(user__username=identifier) |
                    Q(user__username__iexact=clean_identifier) |
                    Q(user__username__iexact=identifier),
                    is_suspended=False
                ).first()
            )
            if not profile:
                raise Http404("Member profile not found.")

        try:
            serializer = MemberProfileDetailSerializer(profile, context={'request': request})
            return Response(serializer.data)
        except Exception:
            # Safe fallback: return member profile attributes with zero stats rather than crashing with 500
            fallback_serializer = MemberProfileListSerializer(profile, context={'request': request})
            fallback_data = fallback_serializer.data
            fallback_data['secondary_position'] = profile.secondary_position
            fallback_data['jersey_picture'] = profile.jersey_picture.url if profile.jersey_picture else None
            fallback_data['bio'] = profile.bio or ''
            fallback_data['football_stats'] = {
                'appearances': 0, 'goals': 0, 'assists': 0, 'player_of_the_match': 0,
                'yellow_cards': 0, 'red_cards': 0, 'appearances_list': [], 'goals_list': [],
                'assists_list': [], 'potm_list': [], 'yellow_cards_list': [], 'red_cards_list': [],
            }
            fallback_data['player_registration'] = None
            fallback_data['awards'] = []
            return Response(fallback_data)


class MemberFollowToggleAPIView(APIView):
    """Toggle follow/unfollow a fellow member."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, member_id):
        target_profile = get_object_or_404(MemberProfile.objects.select_related('user'), id=member_id)
        current_user = request.user
        target_user = target_profile.user

        if current_user == target_user:
            return Response(
                {"error": "You cannot follow your own profile."},
                status=status.HTTP_400_BAD_REQUEST
            )

        with transaction.atomic():
            follow_relation = MemberFollow.objects.filter(
                follower=current_user,
                following=target_user
            ).first()

            current_profile = getattr(current_user, 'profile', None)

            if follow_relation:
                # Unfollow
                follow_relation.delete()
                MemberProfile.objects.filter(user=target_user).update(
                    followers_count=F('followers_count') - 1
                )
                if current_profile:
                    MemberProfile.objects.filter(user=current_user).update(
                        following_count=F('following_count') - 1
                    )
                target_profile.refresh_from_db()
                return Response({
                    'status': 'unfollowed',
                    'message': f"You have unfollowed {target_profile.full_name}.",
                    'followers_count': target_profile.followers_count,
                    'is_following': False,
                })
            else:
                # Follow
                MemberFollow.objects.create(follower=current_user, following=target_user)
                MemberProfile.objects.filter(user=target_user).update(
                    followers_count=F('followers_count') + 1
                )
                if current_profile:
                    MemberProfile.objects.filter(user=current_user).update(
                        following_count=F('following_count') + 1
                    )

                # Send Notification
                follower_name = current_profile.full_name if current_profile else current_user.username
                Notification.objects.create(
                    recipient=target_user,
                    actor=current_user,
                    verb=f"{follower_name} started following your profile.",
                    target_url=f"/members/{current_user.username}"
                )

                target_profile.refresh_from_db()
                return Response({
                    'status': 'followed',
                    'message': f"You are now following {target_profile.full_name}!",
                    'followers_count': target_profile.followers_count,
                    'is_following': True,
                })


class MemberFollowersListAPIView(generics.ListAPIView):
    serializer_class = MemberProfileListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        member_id = self.kwargs.get('member_id')
        target_profile = get_object_or_404(MemberProfile, id=member_id)
        follower_users = MemberFollow.objects.filter(
            following=target_profile.user
        ).values_list('follower', flat=True)
        return MemberProfile.objects.filter(user__in=follower_users).select_related('user')


class MemberFollowingListAPIView(generics.ListAPIView):
    serializer_class = MemberProfileListSerializer
    permission_classes = [permissions.AllowAny]

    def get_queryset(self):
        member_id = self.kwargs.get('member_id')
        target_profile = get_object_or_404(MemberProfile, id=member_id)
        following_users = MemberFollow.objects.filter(
            follower=target_profile.user
        ).values_list('following', flat=True)
        return MemberProfile.objects.filter(user__in=following_users).select_related('user')


class UpdateMyProfileAPIView(APIView):
    """Allows authenticated user to update their personal and football details."""
    permission_classes = [permissions.IsAuthenticated]

    def patch(self, request):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({"error": "Profile not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = MemberProfileUpdateSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            # Also update User first/last name if supplied
            if 'first_name' in serializer.validated_data:
                request.user.first_name = serializer.validated_data['first_name']
            if 'second_name' in serializer.validated_data:
                request.user.last_name = serializer.validated_data['second_name']
            request.user.save()
            return Response(MemberProfileDetailSerializer(profile, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class ApplyPlayerRegistrationAPIView(APIView):
    """Allows an eligible member to register for their batch roster in the active season."""
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        profile = getattr(request.user, 'profile', None)
        if not profile:
            return Response({"error": "Member profile required."}, status=status.HTTP_400_BAD_REQUEST)

        # Eligibility check
        if not profile.is_football_eligible or not profile.competing_batch:
            return Response(
                {"error": "You are not eligible to register for official competition rosters based on your academic batch/year."},
                status=status.HTTP_403_FORBIDDEN
            )

        active_season = Season.objects.filter(is_active=True).first() or Season.objects.first()
        if not active_season:
            return Response({"error": "No active competition season available."}, status=status.HTTP_400_BAD_REQUEST)

        # Check existing registration
        existing = PlayerRegistration.objects.filter(member=profile, season=active_season).first()
        if existing:
            return Response(
                {"error": f"You already have a {existing.status.lower()} registration for {active_season.name}."},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Find matching BatchTeam
        batch_team = BatchTeam.objects.filter(batch_code=profile.competing_batch).first()
        if not batch_team:
            return Response(
                {"error": f"Batch team '{profile.get_competing_batch_display()}' is not registered."},
                status=status.HTTP_400_BAD_REQUEST
            )

        position = request.data.get('preferred_position') or profile.primary_position or 'Midfielder'
        jersey_number = request.data.get('jersey_number') or profile.preferred_jersey_number or 10
        notes = request.data.get('football_notes', '')

        registration = PlayerRegistration.objects.create(
            member=profile,
            season=active_season,
            batch_team=batch_team,
            preferred_position=position,
            jersey_number=jersey_number,
            football_notes=notes,
            status='PENDING'
        )

        serializer = PlayerRegistrationSerializer(registration)
        return Response({
            'message': f"Application submitted! Pending manager approval for {batch_team.name}.",
            'registration': serializer.data
        }, status=status.HTTP_201_CREATED)

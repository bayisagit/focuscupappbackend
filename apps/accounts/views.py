from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from apps.accounts.serializers import RegisterSerializer, UserSummarySerializer
from apps.members.models import MemberProfile, PlayerRegistration

User = get_user_model()


def get_user_coach_info(user):
    if not getattr(user, 'is_coach', False):
        return {
            'is_coach': False,
            'coached_batch': None,
            'coached_batch_name': None,
            'coached_batch_id': None,
            'coached_team': None,
        }

    coached_team = None
    if hasattr(user, 'coached_batch_team') and user.coached_batch_team:
        coached_team = user.coached_batch_team
    elif hasattr(user, 'coached_teams'):
        coached_team = user.coached_teams.first()

    coach_member = coached_team.coach_member if coached_team else getattr(user, 'linked_member', None)
    if not coach_member and hasattr(user, 'profile'):
        coach_member = user.profile

    avatar = None
    if coach_member:
        avatar = getattr(coach_member, 'avatar_url', None) or getattr(coach_member, 'profile_picture_url', None)
        if not avatar and getattr(coach_member, 'profile_picture', None):
            try:
                avatar = coach_member.profile_picture.url
            except Exception:
                avatar = str(coach_member.profile_picture)
    coach_full_name = coach_member.full_name if coach_member else None

    return {
        'is_coach': True,
        'coached_batch': coached_team.batch_code if coached_team else None,
        'coached_batch_name': coached_team.name if coached_team else None,
        'coached_batch_id': coached_team.id if coached_team else None,
        'coach_name': coach_full_name,
        'coach_avatar_url': avatar,
        'coach_photo_url': avatar,
        'coach_member': {
            'id': coach_member.id,
            'full_name': coach_full_name,
            'avatar_url': avatar,
            'photo_url': avatar,
            'department': coach_member.department,
            'username': coach_member.user.username if coach_member and coach_member.user else '',
        } if coach_member else None,
        'coached_team': {
            'id': coached_team.id,
            'batch_code': coached_team.batch_code,
            'name': coached_team.name,
            'nickname': coached_team.nickname,
            'color_hex': coached_team.color_hex,
            'photo_url': coached_team.photo_url,
            'coach_name': coach_full_name,
            'coach_photo_url': avatar,
        } if coached_team else None,
    }


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):
        username_or_email = attrs.get('username', '').strip()
        if '@' in username_or_email:
            matched_user = User.objects.filter(email__iexact=username_or_email).first()
            if matched_user:
                attrs['username'] = matched_user.username
        elif username_or_email:
            matched_user = User.objects.filter(username__iexact=username_or_email).first()
            if matched_user:
                attrs['username'] = matched_user.username

        data = super().validate(attrs)
        coach_info = get_user_coach_info(self.user)

        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'is_manager': self.user.is_manager,
            'is_coach': coach_info['is_coach'],
            'coached_batch': coach_info['coached_batch'],
            'coached_batch_name': coach_info['coached_batch_name'],
            'coached_batch_id': coach_info['coached_batch_id'],
            'coached_team': coach_info['coached_team'],
            'coach_name': coach_info.get('coach_name'),
            'coach_avatar_url': coach_info.get('coach_avatar_url'),
            'coach_photo_url': coach_info.get('coach_photo_url'),
            'coach_member': coach_info.get('coach_member'),
        }

        # Resolve member profile (either directly on user, or via linked_member for coach account)
        prof = getattr(self.user, 'profile', None) or getattr(self.user, 'linked_member', None)
        if prof:
            data['user']['profile'] = {
                'id': prof.id,
                'first_name': prof.first_name,
                'second_name': prof.second_name,
                'full_name': prof.full_name,
                'batch': prof.get_competing_batch_display() or prof.academic_year,
                'competing_batch': prof.competing_batch,
                'college': prof.get_college_display(),
                'department': prof.department,
                'fellowship_team': prof.fellowship_team,
                'gender': prof.gender,
                'academic_year': prof.academic_year,
                'primary_position': prof.primary_position,
                'secondary_position': prof.secondary_position,
                'preferred_jersey_number': prof.preferred_jersey_number,
                'personal_chant': prof.personal_chant,
                'bio': prof.bio,
                'is_football_eligible': prof.is_football_eligible,
                'profile_picture': prof.avatar_url,
                'avatar_url': prof.avatar_url,
                'profile_picture_url': prof.profile_picture_url,
            }
        return data


class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            refresh = RefreshToken.for_user(user)
            prof = user.profile
            return Response({
                'message': 'Registration successful! Welcome to AASTU Focus Fellowship.',
                'tokens': {
                    'refresh': str(refresh),
                    'access': str(refresh.access_token),
                },
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'role': user.role,
                    'is_manager': user.is_manager,
                    'profile': {
                        'id': prof.id,
                        'first_name': prof.first_name,
                        'second_name': prof.second_name,
                        'full_name': prof.full_name,
                        'batch': prof.get_competing_batch_display() or prof.academic_year,
                        'competing_batch': prof.competing_batch,
                        'college': prof.get_college_display(),
                        'department': prof.department,
                        'fellowship_team': prof.fellowship_team,
                        'gender': prof.gender,
                        'academic_year': prof.academic_year,
                        'primary_position': prof.primary_position,
                        'secondary_position': prof.secondary_position,
                        'preferred_jersey_number': prof.preferred_jersey_number,
                        'personal_chant': prof.personal_chant,
                        'bio': prof.bio,
                        'is_football_eligible': prof.is_football_eligible,
                    }
                }
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        user = request.user
        prof = getattr(user, 'profile', None) or getattr(user, 'linked_member', None)
        coach_info = get_user_coach_info(user)

        profile_data = None
        player_registration = None
        if prof:
            profile_data = {
                'id': prof.id,
                'first_name': prof.first_name,
                'second_name': prof.second_name,
                'full_name': prof.full_name,
                'college': prof.college,
                'college_display': prof.get_college_display(),
                'department': prof.department,
                'academic_year': prof.academic_year,
                'fellowship_team': prof.fellowship_team,
                'gender': prof.gender,
                'primary_position': prof.primary_position,
                'secondary_position': prof.secondary_position,
                'preferred_jersey_number': prof.preferred_jersey_number,
                'profile_picture': prof.avatar_url,
                'avatar_url': prof.avatar_url,
                'profile_picture_url': prof.profile_picture_url,
                'jersey_picture': prof.jersey_picture.url if prof.jersey_picture else None,
                'bio': prof.bio,
                'personal_chant': prof.personal_chant,
                'followers_count': prof.followers_count,
                'following_count': prof.following_count,
                'is_football_eligible': prof.is_football_eligible,
                'competing_batch': prof.competing_batch,
                'competing_batch_display': prof.get_competing_batch_display(),
            }

            # Check for latest player registration
            reg = PlayerRegistration.objects.filter(member=prof).order_by('-created_at').first()
            if reg:
                player_registration = {
                    'id': reg.id,
                    'season_name': reg.season.name,
                    'batch_name': reg.batch_team.name,
                    'jersey_number': reg.jersey_number,
                    'preferred_position': reg.preferred_position,
                    'status': reg.status,
                    'rejection_reason': reg.rejection_reason if reg.status == 'REJECTED' else None,
                }

        return Response({
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'role': user.role,
            'is_manager': user.is_manager,
            'is_coach': coach_info['is_coach'],
            'coached_batch': coach_info['coached_batch'],
            'coached_batch_name': coach_info['coached_batch_name'],
            'coached_batch_id': coach_info['coached_batch_id'],
            'coached_team': coach_info['coached_team'],
            'coach_name': coach_info.get('coach_name'),
            'coach_avatar_url': coach_info.get('coach_avatar_url'),
            'coach_photo_url': coach_info.get('coach_photo_url'),
            'coach_member': coach_info.get('coach_member'),
            'profile': profile_data,
            'player_registration': player_registration,
        })


class PasswordResetView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get('email')
        new_password = request.data.get('new_password')
        if not email or not new_password:
            return Response(
                {"error": "Please provide both email and new_password."},
                status=status.HTTP_400_BAD_REQUEST
            )
        try:
            user = User.objects.get(email=email)
            user.set_password(new_password)
            user.save()
            return Response({"message": "Password has been successfully updated. You may now login."})
        except User.DoesNotExist:
            return Response(
                {"error": "No account found with this email address."},
                status=status.HTTP_404_NOT_FOUND
            )

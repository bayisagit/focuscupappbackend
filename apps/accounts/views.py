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
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
            'role': self.user.role,
            'is_manager': self.user.is_manager,
        }
        if hasattr(self.user, 'profile'):
            prof = self.user.profile
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
                'profile_picture': prof.profile_picture.url if prof.profile_picture else None,
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
        prof = getattr(user, 'profile', None)

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
                'profile_picture': prof.profile_picture.url if prof.profile_picture else None,
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

from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from apps.members.models import MemberProfile
from apps.members.constants import validate_academic_eligibility

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)
    
    # MemberProfile fields
    first_name = serializers.CharField(required=True)
    second_name = serializers.CharField(required=True)
    college = serializers.CharField(required=True)
    department = serializers.CharField(required=True)
    academic_year = serializers.CharField(required=True)
    fellowship_team = serializers.CharField(required=True)
    gender = serializers.CharField(required=True)
    primary_position = serializers.CharField(required=False, allow_blank=True, default='')
    personal_chant = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = User
        fields = [
            'username', 'email', 'password', 'password_confirm',
            'first_name', 'second_name', 'college', 'department',
            'academic_year', 'fellowship_team', 'gender',
            'primary_position', 'personal_chant'
        ]

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Passwords do not match."})

        # Validate academic eligibility
        is_valid, err_msg, is_eligible, batch = validate_academic_eligibility(
            attrs['college'], attrs['department'], attrs['academic_year']
        )
        if not is_valid:
            raise serializers.ValidationError({"academic_year": err_msg})

        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        profile_data = {
            'first_name': validated_data.pop('first_name'),
            'second_name': validated_data.pop('second_name'),
            'college': validated_data.pop('college'),
            'department': validated_data.pop('department'),
            'academic_year': validated_data.pop('academic_year'),
            'fellowship_team': validated_data.pop('fellowship_team'),
            'gender': validated_data.pop('gender'),
            'primary_position': validated_data.pop('primary_position', ''),
            'personal_chant': validated_data.pop('personal_chant', ''),
        }

        # Manager role cannot be self-registered
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=profile_data['first_name'],
            last_name=profile_data['second_name'],
            role='MEMBER'
        )

        MemberProfile.objects.create(user=user, **profile_data)
        return user


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'role', 'is_manager', 'created_at']

from django.urls import path
from apps.members.views import (
    AcademicOptionsAPIView,
    MemberListAPIView,
    MemberDetailAPIView,
    MemberFollowToggleAPIView,
    MemberFollowersListAPIView,
    MemberFollowingListAPIView,
    UpdateMyProfileAPIView,
    ApplyPlayerRegistrationAPIView,
    BatchJerseyNumbersAPIView,
)

urlpatterns = [
    path('', MemberListAPIView.as_view(), name='member_list'),
    path('options/', AcademicOptionsAPIView.as_view(), name='academic_options'),
    path('me/update/', UpdateMyProfileAPIView.as_view(), name='member_update_profile'),
    path('apply-player/', ApplyPlayerRegistrationAPIView.as_view(), name='member_apply_player'),
    path('batch-jerseys/', BatchJerseyNumbersAPIView.as_view(), name='batch_jerseys'),
    path('<str:identifier>/', MemberDetailAPIView.as_view(), name='member_detail'),
    path('<int:member_id>/follow/', MemberFollowToggleAPIView.as_view(), name='member_follow_toggle'),
    path('<int:member_id>/followers/', MemberFollowersListAPIView.as_view(), name='member_followers'),
    path('<int:member_id>/following/', MemberFollowingListAPIView.as_view(), name='member_following'),
]

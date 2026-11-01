from django.urls import path
from apps.core.views import SiteSettingAPIView
from apps.core.manager_views import (
    ManagerDashboardAPIView,
    ManagerMemberListAPIView,
    ManagerMemberSuspendToggleAPIView,
    ManagerPlayerRegistrationsAPIView,
    ManagerPlayerReviewAPIView,
    ManagerGenerateFixturesAPIView,
    ManagerCreateFixtureAPIView,
    ManagerMatchUpdateAPIView,
    ManagerMatchPublishAPIView,
    ManagerMatchCorrectAPIView,
    ManagerMatchEventAPIView,
    ManagerAuditLogListAPIView,
    ManagerExportAPIView,
)

urlpatterns = [
    # Public core settings
    path('settings/', SiteSettingAPIView.as_view(), name='site_settings'),

    # Manager Administration Endpoints
    path('manager/dashboard/', ManagerDashboardAPIView.as_view(), name='manager_dashboard'),
    path('manager/members/', ManagerMemberListAPIView.as_view(), name='manager_members'),
    path('manager/members/<int:member_id>/suspend/', ManagerMemberSuspendToggleAPIView.as_view(), name='manager_member_suspend'),
    path('manager/player-registrations/', ManagerPlayerRegistrationsAPIView.as_view(), name='manager_player_registrations'),
    path('manager/player-registrations/<int:registration_id>/review/', ManagerPlayerReviewAPIView.as_view(), name='manager_player_review'),
    path('manager/generate-fixtures/', ManagerGenerateFixturesAPIView.as_view(), name='manager_generate_fixtures'),
    path('manager/fixtures/create/', ManagerCreateFixtureAPIView.as_view(), name='manager_create_fixture'),
    path('manager/matches/<int:match_id>/update/', ManagerMatchUpdateAPIView.as_view(), name='manager_match_update'),
    path('manager/matches/<int:match_id>/publish/', ManagerMatchPublishAPIView.as_view(), name='manager_match_publish'),
    path('manager/matches/<int:match_id>/correct/', ManagerMatchCorrectAPIView.as_view(), name='manager_match_correct'),
    path('manager/matches/<int:match_id>/events/', ManagerMatchEventAPIView.as_view(), name='manager_match_events'),
    path('manager/audit-logs/', ManagerAuditLogListAPIView.as_view(), name='manager_audit_logs'),
    path('manager/export/<str:data_type>/', ManagerExportAPIView.as_view(), name='manager_export'),
]

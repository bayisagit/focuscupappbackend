
# pyrefly: ignore[untyped-import]
from django.urls import path
from apps.core.views import SiteSettingAPIView
from apps.core.manager_views import (
    ManagerDashboardAPIView,
    ManagerMemberListAPIView,
    ManagerMemberSuspendToggleAPIView,
    ManagerMemberDeleteAPIView,
    ManagerPlayerRegistrationsAPIView,
    ManagerPlayerReviewAPIView,
    ManagerGenerateFixturesAPIView,
    ManagerCreateFixtureAPIView,
    ManagerMatchUpdateAPIView,
    ManagerMatchSquadAPIView,
    ManagerMatchPublishAPIView,
    ManagerMatchCorrectAPIView,
    ManagerMatchEventAPIView,
    ManagerAuditLogListAPIView,
    ManagerExportAPIView,
    ManagerMigrateAPIView,
    ManagerBatchCoachesAPIView,
    ManagerAssignCoachAPIView,
    ManagerRevokeCoachAPIView,
)
from apps.core.coach_views import (
    CoachDashboardAPIView,
    CoachPlayerRegistrationsAPIView,
    CoachPlayerReviewAPIView,
    CoachMatchesAPIView,
    CoachMatchSquadAPIView,
)

urlpatterns = [
    # Public core settings
    path('settings/', SiteSettingAPIView.as_view(), name='site_settings'),
    path('maintenance/migrate/', ManagerMigrateAPIView.as_view(), name='maintenance_migrate'),

    # Manager Administration Endpoints
    path('manager/dashboard/', ManagerDashboardAPIView.as_view(), name='manager_dashboard'),
    path('manager/members/', ManagerMemberListAPIView.as_view(), name='manager_members'),
    path('manager/members/<int:member_id>/suspend/', ManagerMemberSuspendToggleAPIView.as_view(), name='manager_member_suspend'),
    path('manager/members/<int:member_id>/delete/', ManagerMemberDeleteAPIView.as_view(), name='manager_member_delete'),
    path('manager/player-registrations/', ManagerPlayerRegistrationsAPIView.as_view(), name='manager_player_registrations'),
    path('manager/player-registrations/<int:registration_id>/review/', ManagerPlayerReviewAPIView.as_view(), name='manager_player_review'),
    path('manager/generate-fixtures/', ManagerGenerateFixturesAPIView.as_view(), name='manager_generate_fixtures'),
    path('manager/fixtures/create/', ManagerCreateFixtureAPIView.as_view(), name='manager_create_fixture'),
    path('manager/matches/<int:match_id>/update/', ManagerMatchUpdateAPIView.as_view(), name='manager_match_update'),
    path('manager/matches/<int:match_id>/squad/', ManagerMatchSquadAPIView.as_view(), name='manager_match_squad'),
    path('manager/matches/<int:match_id>/publish/', ManagerMatchPublishAPIView.as_view(), name='manager_match_publish'),
    path('manager/matches/<int:match_id>/correct/', ManagerMatchCorrectAPIView.as_view(), name='manager_match_correct'),
    path('manager/matches/<int:match_id>/events/', ManagerMatchEventAPIView.as_view(), name='manager_match_events'),
    path('manager/audit-logs/', ManagerAuditLogListAPIView.as_view(), name='manager_audit_logs'),
    path('manager/export/<str:data_type>/', ManagerExportAPIView.as_view(), name='manager_export'),

    # Manager Coach Management
    path('manager/coaches/', ManagerBatchCoachesAPIView.as_view(), name='manager_batch_coaches'),
    path('manager/coaches/assign/', ManagerAssignCoachAPIView.as_view(), name='manager_assign_coach'),
    path('manager/coaches/revoke/', ManagerRevokeCoachAPIView.as_view(), name='manager_revoke_coach'),

    # Dedicated Batch Coach Endpoints
    path('coach/dashboard/', CoachDashboardAPIView.as_view(), name='coach_dashboard'),
    path('coach/players/', CoachPlayerRegistrationsAPIView.as_view(), name='coach_player_registrations'),
    path('coach/players/<int:registration_id>/review/', CoachPlayerReviewAPIView.as_view(), name='coach_player_review'),
    path('coach/matches/', CoachMatchesAPIView.as_view(), name='coach_matches'),
    path('coach/matches/<int:match_id>/squad/', CoachMatchSquadAPIView.as_view(), name='coach_match_squad'),
]

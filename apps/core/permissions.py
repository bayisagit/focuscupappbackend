from rest_framework import permissions

class IsTournamentManager(permissions.BasePermission):
    """
    Allows access only to authenticated managers (role='MANAGER', is_staff, or is_superuser).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            request.user.is_manager
        )


class IsBatchCoach(permissions.BasePermission):
    """
    Allows access only to authenticated batch coaches (role='COACH' or has coached_batch_team).
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            getattr(request.user, 'is_coach', False)
        )


class IsTournamentManagerOrBatchCoach(permissions.BasePermission):
    """
    Allows access to tournament managers or authenticated batch coaches.
    """
    def has_permission(self, request, view):
        return bool(
            request.user and
            request.user.is_authenticated and
            (getattr(request.user, 'is_manager', False) or getattr(request.user, 'is_coach', False))
        )

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

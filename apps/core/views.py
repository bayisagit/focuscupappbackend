from rest_framework import permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.core.models import SiteSetting
from apps.core.serializers import SiteSettingSerializer
from apps.core.permissions import IsTournamentManager


class SiteSettingAPIView(APIView):
    """Public read of site title, motto, and social links; Manager update."""
    def get_permissions(self):
        if self.request.method in ('PATCH', 'PUT'):
            return [IsTournamentManager()]
        return [permissions.AllowAny()]

    def get(self, request):
        setting = SiteSetting.get_settings()
        return Response(SiteSettingSerializer(setting).data)

    def patch(self, request):
        setting = SiteSetting.get_settings()
        serializer = SiteSettingSerializer(setting, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

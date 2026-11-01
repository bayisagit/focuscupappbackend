"""
URL configuration for focus_cup project.
AASTU Focus Fellowship – Focus Football Cup.
"""

from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

# Customize Django Admin branding
admin.site.site_header = "AASTU Focus Fellowship – Focus Football Cup Admin"
admin.site.site_title = "Focus Cup Admin Portal"
admin.site.index_title = "Tournament & Community Administration"

urlpatterns = [
    # Django Admin
    path('admin/', admin.site.urls),

    # API v1 Endpoints
    path('api/v1/auth/', include('apps.accounts.urls')),
    path('api/v1/members/', include('apps.members.urls')),
    path('api/v1/competitions/', include('apps.competitions.urls')),
    path('api/v1/matches/', include('apps.matches.urls')),
    path('api/v1/statistics/', include('apps.statistics.urls')),
    path('api/v1/community/', include('apps.community.urls')),
    path('api/v1/', include('apps.core.urls')),

    # Swagger / OpenAPI Documentation
    path('api/schema/', SpectacularAPIView.as_view(), name='schema'),
    path('api/docs/', SpectacularSwaggerView.as_view(url_name='schema'), name='swagger-ui'),
    path('api/redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]

# Serve media and static files in development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)

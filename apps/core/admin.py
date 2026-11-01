from django.contrib import admin
from apps.core.models import SiteSetting


@admin.register(SiteSetting)
class SiteSettingAdmin(admin.ModelAdmin):
    list_display = ('site_title', 'tagline', 'verse_reference', 'updated_at')

    def has_add_permission(self, request):
        # Singleton setting: only one allowed
        if SiteSetting.objects.exists():
            return False
        return True

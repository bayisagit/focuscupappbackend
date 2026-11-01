from rest_framework import serializers
from apps.core.models import SiteSetting


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = [
            'id', 'site_title', 'tagline', 'about_fellowship',
            'verse_text', 'verse_reference', 'facebook_url',
            'telegram_url', 'tiktok_url', 'instagram_url',
            'youtube_url', 'contact_email', 'contact_phone', 'updated_at'
        ]

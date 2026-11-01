from rest_framework import serializers
from apps.core.models import SiteSetting


class SiteSettingSerializer(serializers.ModelSerializer):
    class Meta:
        model = SiteSetting
        fields = [
            'id', 'site_title', 'tagline', 'about_fellowship',
            'verse_text', 'verse_reference', 'telegram_url',
            'facebook_url', 'youtube_url', 'instagram_url',
            'contact_email', 'contact_phone', 'updated_at'
        ]

from django.db import models


class SiteSetting(models.Model):
    site_title = models.CharField(
        max_length=200,
        default="AASTU Focus Fellowship – Focus Football Cup"
    )
    tagline = models.CharField(
        max_length=255,
        default="Winning is a bonus; friendship, joy, and fellowship come first!"
    )
    about_fellowship = models.TextField(
        default=(
            "Focus Fellowship at Addis Ababa Science and Technology University (AASTU) "
            "is a Christ-centered university student community dedicated to spiritual growth, "
            "academic excellence, genuine brotherly and sisterly fellowship, and building "
            "lasting friendships across academic batches."
        )
    )
    verse_text = models.CharField(
        max_length=255,
        default="Behold, how good and pleasant it is when brothers and sisters dwell together in unity!"
    )
    verse_reference = models.CharField(max_length=100, default="Psalm 133:1")

    # Configurable social and contact links
    facebook_url = models.URLField(blank=True, default="https://web.facebook.com/fstufocus")
    telegram_url = models.URLField(blank=True, default="https://t.me/fstufocus")
    tiktok_url = models.URLField(blank=True, default="https://www.tiktok.com/@aastu_focus?lang=en")
    instagram_url = models.URLField(blank=True, default="https://www.instagram.com/aastufocus/")
    youtube_url = models.URLField(blank=True, default="https://www.youtube.com/@aastufocusofficial9025")
    contact_email = models.EmailField(blank=True, default="contact@aastufocus.org")
    contact_phone = models.CharField(max_length=50, blank=True, default="+25191 784 1282")

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Site & Fellowship Setting'
        verbose_name_plural = 'Site & Fellowship Settings'

    def __str__(self):
        return self.site_title

    @classmethod
    def get_settings(cls):
        obj = cls.objects.first()
        if not obj:
            obj = cls.objects.create()
        return obj

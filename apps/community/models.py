from django.db import models
from django.conf import settings


class Announcement(models.Model):
    CATEGORY_CHOICES = [
        ('TOURNAMENT', 'Tournament Notice'),
        ('FELLOWSHIP', 'Fellowship Family News'),
        ('SPIRITUAL', 'Encouragement & Prayer'),
        ('MATCH_DAY', 'Match Day Information'),
    ]

    PRIORITY_CHOICES = [
        ('NORMAL', 'Standard Announcement'),
        ('IMPORTANT', 'Important Notice'),
        ('URGENT', 'Urgent Alert'),
    ]

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, default='TOURNAMENT')
    priority = models.CharField(max_length=20, choices=PRIORITY_CHOICES, default='NORMAL')
    content = models.TextField()
    is_pinned = models.BooleanField(default=False, help_text="Pinned announcements appear at the top of the homepage")
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='announcements'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-is_pinned', '-created_at']
        verbose_name = 'Announcement'
        verbose_name_plural = 'Announcements'

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title}"


class GalleryAlbum(models.Model):
    title = models.CharField(max_length=150)
    description = models.TextField(blank=True, default='')
    cover_photo = models.ImageField(upload_to='gallery/covers/', null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Gallery Album'
        verbose_name_plural = 'Gallery Albums'

    def __str__(self):
        return self.title


class GalleryPhoto(models.Model):
    album = models.ForeignKey(GalleryAlbum, on_delete=models.CASCADE, related_name='photos')
    image = models.ImageField(upload_to='gallery/photos/', null=True, blank=True)
    image_url = models.CharField(
        max_length=500,
        blank=True,
        default='',
        help_text="Cloudinary CDN URL for shared match or fellowship photo"
    )
    caption = models.CharField(max_length=255, blank=True, default='')

    @property
    def photo_url(self):
        if self.image_url:
            return self.image_url
        if self.image:
            try:
                return self.image.url
            except Exception:
                return str(self.image)
        return ''
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='uploaded_photos'
    )
    is_approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Gallery Photo'
        verbose_name_plural = 'Gallery Photos'

    def __str__(self):
        return f"{self.album.title} - Photo #{self.id}"


class Notification(models.Model):
    recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='notifications'
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='triggered_notifications'
    )
    verb = models.CharField(max_length=255)
    target_url = models.CharField(max_length=255, blank=True, default='')
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Notification'
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"Notification for {self.recipient.username}: {self.verb}"

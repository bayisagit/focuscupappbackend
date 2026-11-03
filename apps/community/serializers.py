from rest_framework import serializers
from apps.community.models import Announcement, GalleryAlbum, GalleryPhoto, Notification


class AnnouncementSerializer(serializers.ModelSerializer):
    author_name = serializers.CharField(source='author.get_full_name', read_only=True)
    category_display = serializers.CharField(source='get_category_display', read_only=True)
    priority_display = serializers.CharField(source='get_priority_display', read_only=True)
    photo_url = serializers.CharField(read_only=True, allow_null=True)
    image_url = serializers.CharField(required=False, allow_blank=True, default='')

    class Meta:
        model = Announcement
        fields = [
            'id', 'title', 'category', 'category_display',
            'priority', 'priority_display', 'content',
            'image_url', 'photo_url', 'is_pinned', 'is_active',
            'author_name', 'created_at'
        ]


class GalleryPhotoSerializer(serializers.ModelSerializer):
    uploaded_by_name = serializers.CharField(source='uploaded_by.get_full_name', read_only=True)
    image = serializers.SerializerMethodField()

    class Meta:
        model = GalleryPhoto
        fields = ['id', 'album', 'image', 'image_url', 'caption', 'uploaded_by_name', 'created_at']

    def get_image(self, obj):
        return obj.photo_url


class GalleryAlbumSerializer(serializers.ModelSerializer):
    photos = serializers.SerializerMethodField()
    photo_count = serializers.SerializerMethodField()

    class Meta:
        model = GalleryAlbum
        fields = ['id', 'title', 'description', 'cover_photo', 'photo_count', 'photos', 'created_at']

    def get_photos(self, obj):
        approved = obj.photos.filter(is_approved=True).order_by('-created_at')[:50]
        return GalleryPhotoSerializer(approved, many=True).data

    def get_photo_count(self, obj):
        return obj.photos.filter(is_approved=True).count()


class NotificationSerializer(serializers.ModelSerializer):
    actor_name = serializers.CharField(source='actor.get_full_name', read_only=True)

    class Meta:
        model = Notification
        fields = ['id', 'verb', 'actor_name', 'target_url', 'is_read', 'created_at']

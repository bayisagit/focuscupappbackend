from django.contrib import admin
from apps.community.models import Announcement, GalleryAlbum, GalleryPhoto, Notification


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'priority', 'is_pinned', 'author', 'created_at')
    list_filter = ('category', 'priority', 'is_pinned', 'created_at')
    search_fields = ('title', 'content')


class GalleryPhotoInline(admin.TabularInline):
    model = GalleryPhoto
    extra = 2


@admin.register(GalleryAlbum)
class GalleryAlbumAdmin(admin.ModelAdmin):
    list_display = ('title', 'created_at')
    search_fields = ('title', 'description')
    inlines = [GalleryPhotoInline]


@admin.register(GalleryPhoto)
class GalleryPhotoAdmin(admin.ModelAdmin):
    list_display = ('album', 'caption', 'uploaded_by', 'is_approved', 'created_at')
    list_filter = ('is_approved', 'album', 'created_at')
    search_fields = ('caption', 'uploaded_by__username')


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('recipient', 'verb', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('recipient__username', 'verb')

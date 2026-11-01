from django.urls import path
from apps.community.views import (
    AnnouncementListAPIView,
    GalleryAlbumListAPIView,
    GalleryPhotoUploadAPIView,
    NotificationListAPIView,
)

urlpatterns = [
    path('announcements/', AnnouncementListAPIView.as_view(), name='community_announcements'),
    path('gallery/', GalleryAlbumListAPIView.as_view(), name='community_gallery'),
    path('gallery/upload/', GalleryPhotoUploadAPIView.as_view(), name='community_gallery_upload'),
    path('notifications/', NotificationListAPIView.as_view(), name='community_notifications'),
]

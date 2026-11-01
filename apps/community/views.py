from rest_framework import permissions, generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from apps.community.models import Announcement, GalleryAlbum, GalleryPhoto, Notification
from apps.community.serializers import (
    AnnouncementSerializer,
    GalleryAlbumSerializer,
    GalleryPhotoSerializer,
    NotificationSerializer,
)


class AnnouncementListAPIView(generics.ListAPIView):
    serializer_class = AnnouncementSerializer
    permission_classes = [permissions.AllowAny]
    queryset = Announcement.objects.all().order_by('-is_pinned', '-created_at')


class GalleryAlbumListAPIView(generics.ListAPIView):
    serializer_class = GalleryAlbumSerializer
    permission_classes = [permissions.AllowAny]
    queryset = GalleryAlbum.objects.all().order_by('-created_at')


class GalleryPhotoUploadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        album_id = request.data.get('album')
        image = request.FILES.get('image')
        caption = request.data.get('caption', '')

        if not album_id or not image:
            return Response({"error": "Album ID and image are required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            album = GalleryAlbum.objects.get(pk=album_id)
        except GalleryAlbum.DoesNotExist:
            return Response({"error": "Album not found."}, status=status.HTTP_404_NOT_FOUND)

        photo = GalleryPhoto.objects.create(
            album=album,
            image=image,
            caption=caption,
            uploaded_by=request.user,
            is_approved=request.user.is_manager  # Auto-approve if manager, else pending review
        )
        return Response({
            'message': 'Photo uploaded successfully!' + (' Pending manager moderation.' if not request.user.is_manager else ''),
            'photo': GalleryPhotoSerializer(photo).data
        }, status=status.HTTP_201_CREATED)


class NotificationListAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        notifs = Notification.objects.filter(recipient=request.user).order_by('-created_at')[:25]
        unread_count = Notification.objects.filter(recipient=request.user, is_read=False).count()
        return Response({
            'unread_count': unread_count,
            'notifications': NotificationSerializer(notifs, many=True).data,
        })

    def post(self, request):
        # Mark all as read
        Notification.objects.filter(recipient=request.user, is_read=False).update(is_read=True)
        return Response({'message': 'All notifications marked as read.'})

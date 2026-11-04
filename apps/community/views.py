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
from apps.core.permissions import IsTournamentManager
from apps.accounts.models import CustomUser
from apps.matches.models import AuditLog


class AnnouncementListAPIView(generics.ListCreateAPIView):
    serializer_class = AnnouncementSerializer

    def get_queryset(self):
        user = self.request.user
        if user and user.is_authenticated and getattr(user, 'is_manager', False):
            return Announcement.objects.all().order_by('-is_pinned', '-created_at')
        return Announcement.objects.filter(is_active=True).order_by('-is_pinned', '-created_at')

    def get_permissions(self):
        if self.request.method == 'POST':
            return [IsTournamentManager()]
        return [permissions.AllowAny()]

    def perform_create(self, serializer):
        announcement = serializer.save(author=self.request.user)

        # Broadcast notification to all active fellowship members
        try:
            active_users = CustomUser.objects.filter(is_active=True).exclude(pk=self.request.user.pk)
            notifs = [
                Notification(
                    recipient=u,
                    actor=self.request.user,
                    verb=f"shared a fellowship announcement: '{announcement.title}'",
                    target_url="/#announcements"
                )
                for u in active_users
            ]
            if notifs:
                Notification.objects.bulk_create(notifs)
        except Exception:
            pass

        # Audit log entry
        try:
            AuditLog.objects.create(
                user=self.request.user,
                action_type='CREATE',
                model_name='Announcement',
                object_id=str(announcement.id),
                object_repr=announcement.title,
                notes=f"Fellowship announcement published by manager {self.request.user.username}."
            )
        except Exception:
            pass


class AnnouncementDetailAPIView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update (suspend/activate, pin/unpin, edit), or permanently delete an announcement."""
    serializer_class = AnnouncementSerializer
    permission_classes = [IsTournamentManager]
    queryset = Announcement.objects.all()

    def perform_destroy(self, instance):
        title = instance.title
        instance_id = str(instance.id)
        instance.delete()
        try:
            AuditLog.objects.create(
                user=self.request.user,
                action_type='DELETE',
                model_name='Announcement',
                object_id=instance_id,
                object_repr=title,
                notes=f"Announcement '{title}' deleted by manager {self.request.user.username}."
            )
        except Exception:
            pass

    def perform_update(self, serializer):
        instance = serializer.save()
        try:
            status_desc = f"active={instance.is_active}, pinned={instance.is_pinned}"
            AuditLog.objects.create(
                user=self.request.user,
                action_type='UPDATE',
                model_name='Announcement',
                object_id=str(instance.id),
                object_repr=instance.title,
                notes=f"Announcement '{instance.title}' updated ({status_desc}) by manager {self.request.user.username}."
            )
        except Exception:
            pass


class GalleryAlbumListAPIView(generics.ListAPIView):
    serializer_class = GalleryAlbumSerializer
    permission_classes = [permissions.AllowAny]
    queryset = GalleryAlbum.objects.all().order_by('-created_at')
    pagination_class = None


class GalleryPhotoUploadAPIView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        count = GalleryPhoto.objects.filter(uploaded_by=request.user).count()
        is_mgr = getattr(request.user, 'is_manager', False)
        return Response({
            'uploaded_count': count,
            'max_allowed': 3,
            'is_manager': is_mgr,
            'can_upload': is_mgr or (count < 3),
            'remaining': 'Unlimited' if is_mgr else max(0, 3 - count),
        })

    def post(self, request):
        # Enforce maximum 3 match photos for regular members
        if not getattr(request.user, 'is_manager', False):
            user_photo_count = GalleryPhoto.objects.filter(uploaded_by=request.user).count()
            if user_photo_count >= 3:
                return Response({
                    "error": "Upload limit reached: Fellowship members can post a maximum of 3 match photos to preserve storage capacity. Tournament managers have unlimited uploads."
                }, status=status.HTTP_400_BAD_REQUEST)

        album_id = request.data.get('album')
        image = request.FILES.get('image')
        raw_image_url = request.data.get('image_url', '')
        image_url = str(raw_image_url).strip() if raw_image_url else ''
        caption = str(request.data.get('caption') or '').strip()

        if not image and not image_url:
            return Response(
                {"error": "Photo (file upload or Cloudinary URL) is required."},
                status=status.HTTP_400_BAD_REQUEST
            )

        album = None
        if album_id:
            try:
                album = GalleryAlbum.objects.get(pk=album_id)
            except (GalleryAlbum.DoesNotExist, ValueError, TypeError):
                album = None

        if not album:
            album = GalleryAlbum.objects.first()
            if not album:
                album = GalleryAlbum.objects.create(
                    title="Focus Cup Opening Match Highlights",
                    description="Joyful moments, prayers, and competitive action from our opening match fixtures."
                )

        photo = GalleryPhoto.objects.create(
            album=album,
            image=image if image else None,
            image_url=image_url if image_url else '',
            caption=caption,
            uploaded_by=request.user,
            is_approved=True  # Auto-approve newly uploaded match photos so they appear instantly
        )
        return Response({
            'message': 'Photo uploaded successfully!',
            'photo': GalleryPhotoSerializer(photo).data,
            'uploaded_count': GalleryPhoto.objects.filter(uploaded_by=request.user).count(),
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

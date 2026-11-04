from django.urls import path
from apps.matches.views import (
    MatchListAPIView,
    MatchDetailAPIView,
    LatestAndNextMatchAPIView,
    MatchGraphicListCreateAPIView,
    MatchGraphicDetailAPIView,
)

urlpatterns = [
    path('', MatchListAPIView.as_view(), name='match_list'),
    path('latest-and-next/', LatestAndNextMatchAPIView.as_view(), name='match_latest_and_next'),
    path('graphics/', MatchGraphicListCreateAPIView.as_view(), name='match_graphics_list_create'),
    path('graphics/<int:pk>/', MatchGraphicDetailAPIView.as_view(), name='match_graphic_detail'),
    path('<int:pk>/', MatchDetailAPIView.as_view(), name='match_detail'),
]

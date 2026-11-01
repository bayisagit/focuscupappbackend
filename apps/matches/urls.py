from django.urls import path
from apps.matches.views import (
    MatchListAPIView,
    MatchDetailAPIView,
    LatestAndNextMatchAPIView,
)

urlpatterns = [
    path('', MatchListAPIView.as_view(), name='match_list'),
    path('latest-and-next/', LatestAndNextMatchAPIView.as_view(), name='match_latest_and_next'),
    path('<int:pk>/', MatchDetailAPIView.as_view(), name='match_detail'),
]

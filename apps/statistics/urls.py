from django.urls import path
from apps.statistics.views import (
    TopScorersAPIView,
    TopAssistsAPIView,
    MostFollowedMembersAPIView,
    TournamentSummaryAPIView,
    AwardsListAPIView,
)

urlpatterns = [
    path('top-scorers/', TopScorersAPIView.as_view(), name='stats_top_scorers'),
    path('top-assists/', TopAssistsAPIView.as_view(), name='stats_top_assists'),
    path('most-followed/', MostFollowedMembersAPIView.as_view(), name='stats_most_followed'),
    path('summary/', TournamentSummaryAPIView.as_view(), name='stats_summary'),
    path('awards/', AwardsListAPIView.as_view(), name='stats_awards'),
]

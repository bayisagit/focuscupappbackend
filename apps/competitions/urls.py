from django.urls import path
from apps.competitions.views import (
    SeasonListAPIView,
    ActiveSeasonAPIView,
    SeasonStandingsAPIView,
    BatchTeamListAPIView,
    BatchTeamDetailAPIView,
)

urlpatterns = [
    path('seasons/', SeasonListAPIView.as_view(), name='season_list'),
    path('seasons/active/', ActiveSeasonAPIView.as_view(), name='active_season'),
    path('seasons/<int:season_id>/standings/', SeasonStandingsAPIView.as_view(), name='season_standings'),
    path('standings/', SeasonStandingsAPIView.as_view(), name='current_standings'),
    path('batches/', BatchTeamListAPIView.as_view(), name='batch_list'),
    path('batches/<str:batch_code>/', BatchTeamDetailAPIView.as_view(), name='batch_detail'),
]

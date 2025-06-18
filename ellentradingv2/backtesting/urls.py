from django.urls import path
from .views import HistoricalSymbolsView, StrategyListView, BacktestView

urlpatterns = [
    path("historical-symbols/", HistoricalSymbolsView.as_view()),
    path("strategies/", StrategyListView.as_view()),
    path("run/", BacktestView.as_view()),
]


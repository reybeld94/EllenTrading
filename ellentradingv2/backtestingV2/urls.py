from django.urls import path
from .views import download_historical_data, run_backtest_view

urlpatterns = [
    path("download_data/", download_historical_data, name="download_historical_data"),
    path("run_backtest/", run_backtest_view),

]

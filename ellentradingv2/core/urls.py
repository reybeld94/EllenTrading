from .views import get_recent_market_data
from django.urls import path
from core.views import list_symbols

urlpatterns = [
    path("api/market_data/<str:ticker>/", get_recent_market_data),
    path("api/symbols/", list_symbols),
]

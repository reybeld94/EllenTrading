from trades.views import close_trade_manually
from trades.views import TradeViewSet, get_trading_metrics
from trades.views import PortfolioView
from rest_framework.routers import DefaultRouter
from django.urls import path, include
from .views import alpaca_webhook


router = DefaultRouter()
router.register(r"trades", TradeViewSet, basename="trade")


urlpatterns = [
    path("api/", include(router.urls)),
    path("api/trades/<int:trade_id>/close/", close_trade_manually),
    path("api/portfolio/", PortfolioView.as_view(), name="portfolio-view"),
    path("api/metrics/", get_trading_metrics),
    path("api/alpaca/webhook/", alpaca_webhook),
]

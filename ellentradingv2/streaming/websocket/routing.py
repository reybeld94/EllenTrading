from django.urls import re_path
from .consumers import *

websocket_urlpatterns = [
    re_path(r'ws/market/(?P<ticker>\w+)/$', MarketConsumer.as_asgi()),
    re_path(r'ws/signals/$', SignalConsumer.as_asgi()),
    re_path(r"ws/trades/$", TradeConsumer.as_asgi()),
    re_path(r"ws/live-prices/$", LivePriceConsumer.as_asgi()),
    re_path(r"ws/portfolio/$", PortfolioConsumer.as_asgi()),
    re_path(r"ws/logs/$", LogConsumer.as_asgi()),
]

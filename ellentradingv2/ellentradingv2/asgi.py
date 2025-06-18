import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack
import streaming.websocket.routing
import warnings
warnings.filterwarnings("ignore", category=FutureWarning)
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ellentradingv2.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AuthMiddlewareStack(
        URLRouter(
            streaming.websocket.routing.websocket_urlpatterns
        )
    ),
})

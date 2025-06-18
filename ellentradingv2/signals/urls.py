from django.urls import path, include
from rest_framework.routers import DefaultRouter
from signals.views import SignalViewSet

router = DefaultRouter()
router.register(r"signals", SignalViewSet, basename="signals")

urlpatterns = [
    path("api/", include(router.urls)),
]

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from strategies.views import OpenStrategyViewSet

router = DefaultRouter()
router.register(r"strategies", OpenStrategyViewSet, basename="strategies")

urlpatterns = [
    path("api/", include(router.urls)),
]

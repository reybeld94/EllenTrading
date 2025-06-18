from django.urls import path, include
from rest_framework.routers import DefaultRouter
from risk.views import RiskSettingsViewSet

router = DefaultRouter()
router.register(r"risk-settings", RiskSettingsViewSet)

urlpatterns = [
    path("api/", include(router.urls)),
]

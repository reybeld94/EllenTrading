from risk.risk_settings import RiskSettings
from risk.serializers import RiskSettingsSerializer
from rest_framework import viewsets

class RiskSettingsViewSet(viewsets.ModelViewSet):
    queryset = RiskSettings.objects.all()
    serializer_class = RiskSettingsSerializer
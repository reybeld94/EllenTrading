from rest_framework import serializers
from risk.risk_settings import RiskSettings

class RiskSettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = RiskSettings
        fields = '__all__'
from rest_framework import serializers
from core.models.marketdatapoint import MarketDataPoint
from risk.risk_settings import RiskSettings
from core.models.symbol import Symbol

class MarketDataPointSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="symbol.name")

    class Meta:
        model = MarketDataPoint
        fields = [
            "symbol",
            "start_time",
            "end_time",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]



class SymbolSerializer(serializers.ModelSerializer):
    class Meta:
        model = Symbol
        fields = ["id", "symbol", "logo_url"]
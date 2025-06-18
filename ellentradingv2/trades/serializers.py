from rest_framework import serializers
from trades.models.trade import Trade
from trades.models.portfolio import Portfolio, Position


class TradeSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="symbol.symbol")
    live_price = serializers.FloatField(source="symbol.live_price", read_only=True)
    logo_url = serializers.URLField(source="symbol.logo_url", read_only=True)
    class Meta:
        model = Trade
        fields = [
            "id",
            "symbol",
            "logo_url",
            "direction",
            "price",
            "quantity",
            "notional",
            "take_profit",
            "stop_loss",
            "trailing_stop",
            "trailing_stop_level",
            "highest_price",
            "exit_price",
            "pnl",
            "status",
            "strategy",
            "confidence_score",
            "executed_at",
            "closed_at",
            "live_price"
        ]


class PositionSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="symbol.symbol")
    current_price = serializers.FloatField(source="symbol.live_price", read_only=True)
    market_value = serializers.SerializerMethodField()
    unrealized_pnl = serializers.SerializerMethodField()

    class Meta:
        model = Position
        fields = ["symbol", "qty", "avg_price", "current_price", "market_value", "unrealized_pnl"]

    def get_market_value(self, obj):
        price = obj.symbol.live_price or 0
        return round(obj.qty * price, 2)

    def get_unrealized_pnl(self, obj):
        price = obj.symbol.live_price or 0
        return round((price - obj.avg_price) * obj.qty, 2)


class PortfolioSerializer(serializers.ModelSerializer):
    positions = PositionSerializer(many=True, read_only=True)

    class Meta:
        model = Portfolio
        fields = ["name", "usd_balance", "positions"]


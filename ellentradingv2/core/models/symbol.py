from core.models.enums import *


class Symbol(models.Model):
    symbol = models.CharField(max_length=20, unique=True)  # ej. AAPL, BTC/USD, EURUSD
    name = models.CharField(max_length=100, blank=True, null=True)  # Apple Inc.
    exchange = models.CharField(max_length=50, blank=True, null=True)  # e.g. NASDAQ
    asset_class = models.CharField(max_length=10, choices=AssetClass.choices, default=AssetClass.EQUITY)

    live_price = models.FloatField(null=True, blank=True)

    logo_url = models.URLField(blank=True, null=True)

    is_active = models.BooleanField(default=True)
    marginable = models.BooleanField(default=False)
    shortable = models.BooleanField(default=False)
    tradable = models.BooleanField(default=True)

    added_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Opcional: relacionar con broker si manejas varios
    source = models.CharField(max_length=50, default="alpaca")

    def __str__(self):
        return f"{self.symbol}"

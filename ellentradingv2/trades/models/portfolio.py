from django.db import models
from core.models.symbol import Symbol

class Portfolio(models.Model):
    name = models.CharField(max_length=50)
    usd_balance = models.FloatField(default=10000)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - ${self.usd_balance:.2f}"


class Position(models.Model):
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="positions")
    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    qty = models.FloatField(default=0)
    avg_price = models.FloatField(default=0)
    last_buy = models.DateTimeField(null=True, blank=True)

    def market_value(self, current_price):
        return self.qty * current_price

    def unrealized_pnl(self, current_price):
        return (current_price - self.avg_price) * self.qty

    def __str__(self):
        return f"{self.symbol.symbol}: {self.qty} @ {self.avg_price}"



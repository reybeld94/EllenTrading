# core/models/simulated_trade.py

from django.db import models
from signals.signal import Signal

class SimulatedTrade(models.Model):
    signal = models.ForeignKey(Signal, on_delete=models.CASCADE, related_name='simulated_trades')

    direction = models.CharField(max_length=10, choices=[("buy", "Buy"), ("sell", "Sell")])
    entry_price = models.FloatField()
    exit_price = models.FloatField()
    entry_time = models.DateTimeField()
    exit_time = models.DateTimeField()

    profit_absolute = models.FloatField()  # $ ganado o perdido
    profit_percent = models.FloatField()   # % sobre capital simulado

    duration_minutes = models.IntegerField()
    was_successful = models.BooleanField()

    # Meta info
    strategy_name = models.CharField(max_length=100)
    timeframe = models.CharField(max_length=10)
    backtest_batch_id = models.CharField(max_length=50, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['strategy_name', 'timeframe']),
            models.Index(fields=['entry_time', 'exit_time']),
        ]

    def __str__(self):
        result = "✅" if self.was_successful else "❌"
        return f"{result} {self.strategy_name} | {self.direction.upper()} | {self.profit_percent:.2f}%"

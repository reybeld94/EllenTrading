# core/models/signal.py

from django.db import models
from backtesting.models.HistoricalMarketDataPoint import HistoricalMarketDataPoint
from strategies.models import OpenStrategy  # si tienes un modelo para estrategias
from core.models.enums import SignalType

class Signal(models.Model):

    market_data = models.ForeignKey(HistoricalMarketDataPoint, on_delete=models.CASCADE, related_name='signals')
    strategy = models.ForeignKey(OpenStrategy, on_delete=models.CASCADE, null=True, blank=True, related_name="backtesting_signals")

    signal = models.CharField(max_length=10, choices=SignalType.choices)
    confidence_score = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField()  # redundante, pero útil para lookup directo
    timeframe = models.CharField(max_length=10)

    is_executed = models.BooleanField(default=False)
    is_from_backtest = models.BooleanField(default=False)
    notes = models.TextField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['timestamp', 'timeframe']),
        ]

    def __str__(self):
        return f"Signal {self.signal.upper()} @ {self.timestamp} ({self.strategy})"

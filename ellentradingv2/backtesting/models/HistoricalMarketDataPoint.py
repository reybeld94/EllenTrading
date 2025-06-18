# core/models/historical_data.py

from django.db import models

class HistoricalMarketDataPoint(models.Model):
    SOURCE_CHOICES = [
        ('alpaca', 'Alpaca'),
        ('binance', 'Binance'),
        ('yfinance', 'Yahoo Finance'),
        ('manual', 'Manual'),
    ]

    symbol = models.CharField(max_length=20)  # Ej: BTC/USD o BTCUSDT
    timeframe = models.CharField(max_length=10)  # Ej: "1m", "5m", "1h"
    timestamp = models.DateTimeField()  # Hora de inicio de la vela

    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()

    source = models.CharField(max_length=20, choices=SOURCE_CHOICES, default='alpaca')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('symbol', 'timeframe', 'timestamp', 'source')
        indexes = [
            models.Index(fields=['symbol', 'timeframe', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.symbol} [{self.timeframe}] @ {self.timestamp} ({self.source})"

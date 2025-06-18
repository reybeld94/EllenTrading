from core.models.enums import *
from .symbol import Symbol

class MarketDataPoint(models.Model):

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    timeframe = models.CharField(max_length=5, choices=Timeframe.choices, default=Timeframe.ONE_MIN)

    # OHLCV data
    open = models.FloatField()
    high = models.FloatField()
    low = models.FloatField()
    close = models.FloatField()
    volume = models.FloatField()
    normalized_volume = models.FloatField(null=True, blank=True)

    # Extended market metrics (Alpaca-compatible)
    vwap = models.FloatField(blank=True, null=True)
    trade_count = models.IntegerField(blank=True, null=True)
    exchange = models.CharField(max_length=20, blank=True, null=True)  # e.g. "NASDAQ"

    # Timestamps
    start_time = models.DateTimeField()  # beginning of the bar
    end_time = models.DateTimeField()    # end of the bar or close time
    received_at = models.DateTimeField(auto_now_add=True)

    # Optional metadata
    is_closed = models.BooleanField(default=False)
    source = models.CharField(max_length=50, default="alpaca_ws")  # source of the data

    class Meta:
        ordering = ["-start_time"]
        indexes = [
            models.Index(fields=["symbol", "timeframe", "start_time"]),
        ]
        unique_together = ("symbol", "timeframe", "start_time")

    def __str__(self):
        return f"{self.symbol} [{self.timeframe}] - {self.start_time.strftime('%Y-%m-%d %H:%M:%S')}"

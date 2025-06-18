from core.models.enums import *
from core.models.symbol import Symbol
from trades.models.trade import Trade
from strategies.models import OpenStrategy

class Signal(models.Model):
    SIGNAL_TIMEFRAMES = [
        ("1m", "1 Minute"),
        ("5m", "5 Minutes"),
        ("15m", "15 Minutes"),
        ("1h", "1 Hour"),
        ("1d", "1 Day"),
    ]

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    signal = models.CharField(max_length=20, choices=SignalType.choices)
    strategy = models.ForeignKey(OpenStrategy, on_delete=models.SET_NULL, null=True, blank=True)
    price = models.FloatField()
    received_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=50, default="alpaca_websocket")
    executed = models.BooleanField(default=False)

    timeframe = models.CharField(max_length=5, choices=SIGNAL_TIMEFRAMES, default="1m")
    confidence_score = models.IntegerField(blank=True, null=True)
    indicators = models.JSONField(blank=True, null=True)
    related_trades = models.ManyToManyField(Trade, blank=True)

    def __str__(self):
        try:
            if self.received_at:
                fecha = self.received_at.strftime('%Y-%m-%d %H:%M:%S')
            elif hasattr(self, 'timestamp') and self.timestamp:
                fecha = self.timestamp.strftime('%Y-%m-%d %H:%M:%S')
            else:
                fecha = "Sin fecha"
        except Exception:
            fecha = "Fecha inválida"

        return f"{self.symbol} - {self.signal.upper()} - {fecha}"

    def save(self, *args, **kwargs):
        if self.strategy is None:
            raise ValueError("No puedes guardar una señal sin estrategia asignada (strategy=None).")
        super().save(*args, **kwargs)

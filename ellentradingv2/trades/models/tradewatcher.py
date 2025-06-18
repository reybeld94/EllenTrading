from django.db import models
from trades.models.trade import Trade

class TradeWatcher(models.Model):
    trade = models.OneToOneField(Trade, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_tradewatcher"

    def __str__(self):
        return f"Watcher para Trade #{self.trade.id} (activo: {self.active})"

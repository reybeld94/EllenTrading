from core.models.enums import *
from core.models.symbol import Symbol


class Trade(models.Model):

    symbol = models.ForeignKey(Symbol, on_delete=models.CASCADE)
    direction = models.CharField(max_length=4, choices=Direction.choices)

    quantity = models.IntegerField(default=0)
    filled_quantity = models.IntegerField(default=0)

    notional = models.FloatField(blank=True, null=True)
    filled_notional = models.FloatField(blank=True, null=True)

    price = models.FloatField()  # Entrada
    exit_price = models.FloatField(blank=True, null=True)
    pnl = models.FloatField(blank=True, null=True)

    take_profit = models.FloatField(blank=True, null=True)
    stop_loss = models.FloatField(blank=True, null=True)

    trailing_stop = models.FloatField(blank=True, null=True)
    trailing_level = models.FloatField(null=True, blank=True)
    highest_price = models.FloatField(blank=True, null=True)

    order_type = models.CharField(max_length=20, choices=OrderType.choices, default=OrderType.MARKET)
    time_in_force = models.CharField(max_length=10, choices=TimeInForce.choices, default=TimeInForce.DAY)

    execution_mode = models.CharField(max_length=10, choices=ExecutionMode.choices)
    status = models.CharField(max_length=20, choices=TradeStatus.choices, default=TradeStatus.EXECUTED)

    submitted_at = models.DateTimeField(blank=True, null=True)
    executed_at = models.DateTimeField(auto_now_add=True)
    filled_at = models.DateTimeField(blank=True, null=True)
    closed_at = models.DateTimeField(blank=True, null=True)
    canceled_at = models.DateTimeField(blank=True, null=True)

    confidence_score = models.IntegerField()
    strategy = models.CharField(max_length=100, blank=True, null=True)

    fees = models.FloatField(blank=True, null=True)
    commission = models.FloatField(blank=True, null=True)
    slippage = models.FloatField(blank=True, null=True)

    max_drawdown = models.FloatField(default=0)
    min_price_seen = models.FloatField(null=True, blank=True)
    max_price_seen = models.FloatField(null=True, blank=True)

    triggered_by = models.ManyToManyField("signals.Signal")
    notes = models.TextField(blank=True)
    broker_order_id = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        db_table = "core_trade"
    @property
    def trailing_stop_level(self):
        if self.trailing_stop and self.highest_price:
            return round(self.highest_price - self.trailing_stop, 2) if self.direction == "buy" else round(self.highest_price + self.trailing_stop, 2)
        return None

    def __str__(self):
        return f"{self.symbol} {self.direction.upper()} @ {self.price} (score {self.confidence_score})"
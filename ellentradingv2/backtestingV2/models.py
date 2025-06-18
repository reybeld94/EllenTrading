from django.db import models
from core.models.symbol import Symbol
from strategies.models import OpenStrategy
from core.models.enums import *

class HistoricalMarketDataPoint(models.Model):

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


class HistoricalLiveTechnicalIndicator(models.Model):
    market_data = models.OneToOneField(HistoricalMarketDataPoint, on_delete=models.CASCADE, related_name='indicators')

    # --- Indicadores de tendencia ---
    sma_9 = models.FloatField(null=True)
    sma_10 = models.FloatField(null=True)
    sma_20 = models.FloatField(null=True)
    sma_21 = models.FloatField(null=True)
    sma_50 = models.FloatField(null=True)
    sma_55 = models.FloatField(null=True)
    sma_100 = models.FloatField(null=True)
    sma_200 = models.FloatField(null=True)

    ema_9 = models.FloatField(null=True)
    ema_12 = models.FloatField(null=True)
    ema_20 = models.FloatField(null=True)
    ema_21 = models.FloatField(null=True)
    ema_26 = models.FloatField(null=True)
    ema_50 = models.FloatField(null=True)
    ema_55 = models.FloatField(null=True)
    ema_100 = models.FloatField(null=True)
    ema_200 = models.FloatField(null=True)

    wma_10 = models.FloatField(null=True)

    macd = models.FloatField(null=True)
    macd_signal = models.FloatField(null=True)
    macd_hist = models.FloatField(null=True)

    adx = models.FloatField(null=True)
    plus_di = models.FloatField(null=True)
    minus_di = models.FloatField(null=True)

    ichimoku_tenkan = models.FloatField(null=True)
    ichimoku_kijun = models.FloatField(null=True)
    ichimoku_span_a = models.FloatField(null=True)
    ichimoku_span_b = models.FloatField(null=True)
    ichimoku_chikou = models.FloatField(null=True)

    parabolic_sar = models.FloatField(null=True)
    supertrend = models.FloatField(null=True)

    # --- Momentum ---
    rsi_14 = models.FloatField(null=True)
    stochastic_k = models.FloatField(null=True)
    stochastic_d = models.FloatField(null=True)
    cci_20 = models.FloatField(null=True)
    roc = models.FloatField(null=True)
    williams_r = models.FloatField(null=True)
    momentum_10 = models.FloatField(null=True)

    # --- Volatilidad ---
    atr_14 = models.FloatField(null=True)
    bollinger_upper = models.FloatField(null=True)
    bollinger_middle = models.FloatField(null=True)
    bollinger_lower = models.FloatField(null=True)
    donchian_upper = models.FloatField(null=True)
    donchian_lower = models.FloatField(null=True)
    keltner_upper = models.FloatField(null=True)
    keltner_lower = models.FloatField(null=True)
    chaikin_volatility = models.FloatField(null=True)

    # --- Volumen ---
    obv = models.FloatField(null=True)
    ad_line = models.FloatField(null=True)
    chaikin_oscillator = models.FloatField(null=True)
    mfi = models.FloatField(null=True)
    volume_sma_20 = models.FloatField(null=True)
    normalized_volume = models.FloatField(null=True)

    # --- Precio derivado ---
    vwap = models.FloatField(null=True)
    slope = models.FloatField(null=True)
    heikin_ashi_close = models.FloatField(null=True)

    # --- Candlestick patterns (booleanos o flags como float 0/1) ---
    bullish_engulfing = models.FloatField(null=True)
    bearish_engulfing = models.FloatField(null=True)
    hammer = models.FloatField(null=True)
    shooting_star = models.FloatField(null=True)
    doji = models.FloatField(null=True)
    morning_star = models.FloatField(null=True)
    evening_star = models.FloatField(null=True)

    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Live Indicators @ {self.market_data.start_time} [{self.market_data.symbol}]"

class HistoricalTrade(models.Model):

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


    @property
    def trailing_stop_level(self):
        if self.trailing_stop and self.highest_price:
            return round(self.highest_price - self.trailing_stop, 2) if self.direction == "buy" else round(self.highest_price + self.trailing_stop, 2)
        return None

    def __str__(self):
        return f"{self.symbol} {self.direction.upper()} @ {self.price} (score {self.confidence_score})"


class HistoricalSignal(models.Model):
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
    related_trades = models.ManyToManyField(HistoricalTrade, blank=True)

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
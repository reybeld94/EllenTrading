# core/models/live_indicator.py
from django.db import models
from core.models.marketdatapoint import MarketDataPoint

class LiveTechnicalIndicator(models.Model):
    market_data = models.OneToOneField(MarketDataPoint, on_delete=models.CASCADE, related_name='indicators')

    # --- Indicadores de tendencia ---
    sma_9 = models.FloatField(null=True)
    sma_10 = models.FloatField(null=True)
    sma_12 = models.FloatField(null=True)
    sma_20 = models.FloatField(null=True)
    sma_21 = models.FloatField(null=True)
    sma_26 = models.FloatField(null=True)
    sma_30 = models.FloatField(null=True)
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

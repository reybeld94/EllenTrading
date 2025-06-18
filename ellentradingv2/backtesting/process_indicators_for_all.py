import pandas as pd
from django.db import transaction
from backtesting.models import HistoricalMarketDataPoint, TechnicalIndicator
from backtesting.indicators import calculate_all_indicators

def process_indicators_for_all(symbol_filter=None, timeframe_filter=None, batch_size=1000):
    queryset = HistoricalMarketDataPoint.objects.filter(indicators__isnull=True)
    if symbol_filter:
        queryset = queryset.filter(symbol=symbol_filter)
    if timeframe_filter:
        queryset = queryset.filter(timeframe=timeframe_filter)

    total = queryset.count()
    print(f"🔍 Procesando {total} velas sin indicadores...")

    for i in range(0, total, batch_size):
        chunk = list(queryset.order_by("timestamp")[i:i + batch_size])
        if not chunk:
            continue

        df = pd.DataFrame([{
            "id": v.id,
            "open": v.open,
            "high": v.high,
            "low": v.low,
            "close": v.close,
            "volume": v.volume,
        } for v in chunk])

        df = calculate_all_indicators(df)

        indicators = []
        for idx, row in df.iterrows():
            try:
                indicators.append(TechnicalIndicator(
                    market_data_id=row["id"],
                    sma_9=row.get("sma_9"),
                    sma_10=row.get("sma_10"),
                    sma_20=row.get("sma_20"),
                    sma_21=row.get("sma_21"),
                    sma_50=row.get("sma_50"),
                    sma_55=row.get("sma_55"),
                    sma_100=row.get("sma_100"),
                    sma_200=row.get("sma_200"),
                    ema_9=row.get("ema_9"),
                    ema_12=row.get("ema_12"),
                    ema_20=row.get("ema_20"),
                    ema_21=row.get("ema_21"),
                    ema_26=row.get("ema_26"),
                    ema_50=row.get("ema_50"),
                    ema_55=row.get("ema_55"),
                    ema_100=row.get("ema_100"),
                    ema_200=row.get("ema_200"),
                    wma_10=row.get("wma_10"),
                    macd=row.get("macd"),
                    macd_signal=row.get("macd_signal"),
                    macd_hist=row.get("macd_hist"),
                    adx=row.get("adx"),
                    plus_di=row.get("plus_di"),
                    minus_di=row.get("minus_di"),
                    ichimoku_tenkan=row.get("ichimoku_tenkan"),
                    ichimoku_kijun=row.get("ichimoku_kijun"),
                    ichimoku_span_a=row.get("ichimoku_span_a"),
                    ichimoku_span_b=row.get("ichimoku_span_b"),
                    ichimoku_chikou=row.get("ichimoku_chikou"),
                    parabolic_sar=row.get("parabolic_sar"),
                    supertrend=row.get("supertrend"),
                    rsi_14=row.get("rsi_14"),
                    stochastic_k=row.get("stochastic_k"),
                    stochastic_d=row.get("stochastic_d"),
                    cci_20=row.get("cci_20"),
                    roc=row.get("roc"),
                    williams_r=row.get("williams_r"),
                    momentum_10=row.get("momentum_10"),
                    atr_14=row.get("atr_14"),
                    bollinger_upper=row.get("bollinger_upper"),
                    bollinger_middle=row.get("bollinger_middle"),
                    bollinger_lower=row.get("bollinger_lower"),
                    donchian_upper=row.get("donchian_upper"),
                    donchian_lower=row.get("donchian_lower"),
                    keltner_upper=row.get("keltner_upper"),
                    keltner_lower=row.get("keltner_lower"),
                    chaikin_volatility=row.get("chaikin_volatility"),
                    obv=row.get("obv"),
                    ad_line=row.get("ad_line"),
                    chaikin_oscillator=row.get("chaikin_oscillator"),
                    mfi=row.get("mfi"),
                    volume_sma_20=row.get("volume_sma_20"),
                    normalized_volume=row.get("normalized_volume"),
                    vwap=row.get("vwap"),
                    slope=row.get("slope"),
                    heikin_ashi_close=row.get("heikin_ashi_close"),
                    bullish_engulfing=float(row.get("bullish_engulfing", 0.0)),
                    bearish_engulfing=float(row.get("bearish_engulfing", 0.0)),
                    hammer=float(row.get("hammer", 0.0)),
                    shooting_star=float(row.get("shooting_star", 0.0)),
                    doji=float(row.get("doji", 0.0)),
                    morning_star=float(row.get("morning_star", 0.0)),
                    evening_star=float(row.get("evening_star", 0.0)),
                ))
            except Exception as e:
                print(f"⚠️ Error en fila {idx}: {e}")

        with transaction.atomic():
            TechnicalIndicator.objects.bulk_create(indicators, batch_size=1000)

        print(f"✅ Procesado bloque {i + 1} / {total}")

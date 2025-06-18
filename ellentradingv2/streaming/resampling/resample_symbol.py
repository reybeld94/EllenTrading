from core.models.marketdatapoint import MarketDataPoint
from core.models.symbol import Symbol
from core.models.livetechnicalindicator import LiveTechnicalIndicator
from django.utils.timezone import make_aware, now
from strategies.indicators.indicators import calculate_all_indicators
from strategies.strategies.runner import run_entry_strategies
from datetime import datetime, timedelta
import pandas as pd
from django.db import close_old_connections
from math import ceil
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


def get_next_aligned_time(start, interval_minutes):
    seconds = int(start.timestamp())
    aligned = ceil(seconds / (interval_minutes * 60)) * (interval_minutes * 60)
    return make_aware(datetime.utcfromtimestamp(aligned))


def resample_symbol_full(symbol: Symbol, base_tf="1m", target_tf="15m", timestamp_cierre=None):
    close_old_connections()

    tf_minutes = {
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
    }

    if target_tf not in tf_minutes:
        async_to_sync(log_event)(f"Timeframe no soportado: {target_tf}", source="streaming", level="ERROR")
        return

    interval = tf_minutes[target_tf]

    if not timestamp_cierre:
        timestamp_cierre = get_next_aligned_time(now(), interval)

    start_from = timestamp_cierre - timedelta(minutes=interval)
    end_until = timestamp_cierre

    bars = MarketDataPoint.objects.filter(
        symbol=symbol,
        timeframe=base_tf,
        is_closed=True,
        start_time__gte=start_from,
        start_time__lt=end_until
    ).order_by("start_time")

    if bars.count() == 0:
        async_to_sync(log_event)(f"No hay velas de 1m para: {symbol.symbol} entre {start_from} y {end_until}", source="streaming", level="ERROR")
        return

    df = pd.DataFrame([{
        "timestamp": b.start_time,
        "open": b.open,
        "high": b.high,
        "low": b.low,
        "close": b.close,
        "volume": b.volume,
    } for b in bars]).set_index("timestamp").sort_index()

    rule = f"{interval}min"
    resampled = df.resample(rule, label="left", closed="left").agg({
        "open": "first",
        "high": "max",
        "low": "min",
        "close": "last",
        "volume": "sum"
    }).dropna()

    new_bars = []
    for index, row in resampled.iterrows():
        start_time = make_aware(index) if not index.tzinfo else index
        end_time = start_time + timedelta(minutes=interval)

        async_to_sync(log_event)(f"Nueva vela de: {target_tf} creada para {symbol.symbol} | {start_time.strftime('%Y-%m-%d %H:%M:%S')}", source="streaming", level="INFO")

        new_bars.append(MarketDataPoint(
            symbol=symbol,
            timeframe=target_tf,
            start_time=start_time,
            end_time=end_time,
            open=row.open,
            high=row.high,
            low=row.low,
            close=row.close,
            volume=row.volume,
            normalized_volume=row.volume,
            vwap=None,
            trade_count=None,
            exchange="resampled",
            is_closed=True,
            source="resampler"
        ))

    MarketDataPoint.objects.bulk_create(new_bars)

    for bar in new_bars:
        history = MarketDataPoint.objects.filter(
            symbol=symbol,
            timeframe=target_tf,
            is_closed=True,
            start_time__lte=bar.start_time
        ).order_by("-start_time")[:200]

        df_full = pd.DataFrame([{
            "timestamp": b.start_time,
            "open": b.open,
            "high": b.high,
            "low": b.low,
            "close": b.close,
            "volume": b.volume,
        } for b in reversed(history)]).set_index("timestamp")

        if df_full.empty:
            continue

        if not df_full.index.tz:
            df_full.index = df_full.index.tz_localize("UTC")

        bar_time = bar.start_time.astimezone(df_full.index.tz)
        df_full = calculate_all_indicators(df_full)

        if bar_time in df_full.index:
            indicators_data = df_full.loc[bar_time].to_dict()
            valid_fields = {
                f.name for f in LiveTechnicalIndicator._meta.get_fields()
                if f.concrete and f.name not in ["id", "market_data", "created_at"]
            }
            cleaned = {k: v for k, v in indicators_data.items() if k in valid_fields}
            LiveTechnicalIndicator.objects.update_or_create(market_data=bar, defaults=cleaned)

    run_entry_strategies(symbol, verbose=True)

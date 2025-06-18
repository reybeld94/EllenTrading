from datetime import datetime, timedelta
from django.utils import timezone


def align_to_minute(dt: datetime, interval: str = "1m"):
    if interval.endswith("m"):
        mins = int(interval[:-1])
        aligned = dt.replace(second=0, microsecond=0)
        return aligned - timedelta(minutes=aligned.minute % mins)
    return dt

def is_market_open(dt: datetime):
    market_open = dt.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = dt.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= dt <= market_close

def is_signal_active(signal, current_time):
    duration = signal.strategy.validity_minutes if signal.strategy else 15
    expires_at = (getattr(signal, "timestamp", None) or getattr(signal, "received_at", None)) + timedelta(minutes=duration)
    return current_time <= expires_at

def get_active_signals(symbol_name, execution_mode="simulated", current_time=None):
    from signals.signal import Signal as LiveSignal
    from backtesting.models.HistoricalSignal import Signal as HistoricalSignal

    if execution_mode == "backtest":
        assert current_time is not None, "❌ current_time debe pasarse en modo backtest"
        signals = HistoricalSignal.objects.filter(market_data__symbol=symbol_name)
    else:
        signals = LiveSignal.objects.filter(symbol__symbol=symbol_name)
        current_time = timezone.now()

    active_signals = []
    for s in signals:
        if is_signal_active(s, current_time):
            active_signals.append(s)
    return active_signals

def normalize_timestamp_by_timeframe(timestamp, timeframe):
    tf_minutes = {
        "1m": 1,
        "5m": 5,
        "15m": 15,
        "30m": 30,
        "1h": 60,
        "4h": 240,
        "1d": 1440
    }

    minutes = tf_minutes.get(timeframe)
    if not minutes:
        raise ValueError(f"❌ Timeframe desconocido: {timeframe}")

    total_minutes = timestamp.hour * 60 + timestamp.minute
    normalized_minutes = (total_minutes // minutes) * minutes
    hour = normalized_minutes // 60
    minute = normalized_minutes % 60

    return timestamp.replace(hour=hour, minute=minute, second=0, microsecond=0)

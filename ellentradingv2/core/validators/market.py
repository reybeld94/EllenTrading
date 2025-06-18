from datetime import datetime
from django.utils.dateparse import parse_datetime


def validate_bar_message(msg):
    if not isinstance(msg, dict):
        raise ValueError("Mensaje inválido, no es un dict")

    if msg.get("T") != "b":
        return None

    required_keys = ["t", "o", "h", "l", "c", "v", "S"]
    for key in required_keys:
        if key not in msg:
            raise ValueError(f"Missing key in bar data: {key}")

    # Parseo del timestamp
    raw_ts = msg["t"]
    if isinstance(raw_ts, str):
        ts = parse_datetime(raw_ts)
        if ts is None:
            raise ValueError(f"Timestamp inválido: {raw_ts}")
    elif isinstance(raw_ts, int):
        ts = datetime.utcfromtimestamp(raw_ts / 1000.0)
    else:
        raise ValueError(f"Formato de timestamp no reconocido: {raw_ts}")

    return {
        "timestamp": ts,
        "open": msg["o"],
        "high": msg["h"],
        "low": msg["l"],
        "close": msg["c"],
        "volume": msg.get("v", 0),
        "symbol": msg["S"],
        "normalized_volume": msg.get("v", 0),
        "vwap": (
            round(((msg["h"] + msg["l"] + msg["c"]) / 3), 5)
        ),
        "trade_count": msg.get("n", None),
        "exchange": msg.get("x", None),
    }

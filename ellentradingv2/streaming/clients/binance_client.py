import asyncio
import websockets
import json
from datetime import datetime, timezone
from streaming.websocket.dispatcher import dispatch_bar_message
from streaming.data.live_prices import LIVE_PRICES
from streaming.websocket import emit_live_prices
BINANCE_US_WS_URL = "wss://stream.binance.us:9443/stream"


SYMBOL_MAP = {
    "BTCUSDT": "BTC",
    "ETHUSDT": "ETH",
    "SOLUSDT": "SOL",
}
async def connect_to_miniticker():
    symbols = ["btcusdt", "ethusdt", "solusdt"]
    streams = "/".join([f"{s}@miniTicker" for s in symbols])
    url = f"wss://stream.binance.us:9443/stream?streams={streams}"

    while True:
        try:
            print("🔌 Conectando al WebSocket de miniTicker...")
            async with websockets.connect(url, ping_interval=None) as ws:
                print("🟢 Conectado a Binance miniTicker")

                while True:
                    msg = await ws.recv()
                    parsed = json.loads(msg)

                    data = parsed.get("data")
                    stream = parsed.get("stream")

                    if data and stream and "miniTicker" in stream:
                        symbol_raw = data.get("s")  # Ej: BTCUSDT
                        price = float(data.get("c"))  # último precio
                        symbol_key = SYMBOL_MAP.get(symbol_raw, symbol_raw)

                        LIVE_PRICES[symbol_key] = price
                        await emit_live_prices()


        except Exception as e:
            print("❌ Error en WebSocket miniTicker:", e)

        print("🔁 Reintentando conexión en 5 segundos...")
        await asyncio.sleep(5)

async def connect_to_binance_us():
    streams = "/".join([f"{sym.lower()}@kline_1m" for sym in SYMBOL_MAP.keys()])
    url = f"{BINANCE_US_WS_URL}?streams={streams}"

    while True:
        try:
            print("🔌 Conectando a Binance US WebSocket...")
            async with websockets.connect(url, ping_interval=None) as ws:
                print("🟢 Conectado a Binance US")

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    kline = data.get("data", {}).get("k", {})
                    symbol = data.get("data", {}).get("s")

                    if not kline or not symbol:
                        continue

                    timestamp_ms = int(kline["t"])
                    timestamp = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).isoformat()

                    bar_msg = {
                        "T": "b",
                        "S": SYMBOL_MAP[symbol],
                        "t": timestamp,  # <-- ahora también string
                        "timestamp": timestamp,
                        "o": float(kline["o"]),
                        "h": float(kline["h"]),
                        "l": float(kline["l"]),
                        "c": float(kline["c"]),
                        "v": float(kline["v"]),
                        "n": kline.get("n", 0),
                        "x": "BINANCE_US"
                    }

                    await dispatch_bar_message(bar_msg)

        except Exception as e:
            print("❌ Error en Binance US WS:", e)

        print("🔁 Reintentando en 5 segundos...")
        await asyncio.sleep(5)

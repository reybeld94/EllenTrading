# coinbase_client.py
import asyncio
import websockets
import json
from datetime import datetime
from collections import defaultdict
from streaming.websocket.dispatcher import dispatch_bar_message
from django.utils.timezone import make_aware

URI = "wss://ws-feed.exchange.coinbase.com"

class CoinbaseClient:
    def __init__(self, symbols):
        self.symbols = symbols  # ["BTC-USD", "ETH-USD"]
        self.candles = defaultdict(dict)  # symbol → minute_str → candle
        self.last_minute = {}  # symbol → last minute seen
        self.live_prices = {}

    def _get_minute_key(self, iso_time):
        return iso_time[:16]  # "YYYY-MM-DDTHH:MM"

    def _get_timestamp_obj(self, minute_str):
        return datetime.fromisoformat(minute_str + ":00")

    async def emit_live_prices_loop(self, interval=5):
        from streaming.websocket.helpers import update_live_prices_bulk
        while True:
            await asyncio.sleep(interval)
            if self.live_prices:
                await update_live_prices_bulk(self.live_prices.copy())

    async def _subscribe(self, websocket):
        msg = {
            "type": "subscribe",
            "channels": [{
                "name": "ticker",
                "product_ids": self.symbols
            }]
        }
        await websocket.send(json.dumps(msg))
        print(f"📡 Subscribed to {self.symbols}")

    def _update_candle(self, symbol, price, size, timestamp):
        minute = self._get_minute_key(timestamp)
        price = float(price)
        size = float(size)

        if symbol in self.last_minute and self.last_minute[symbol] != minute:
            prev_minute = self.last_minute[symbol]
            candle = self.candles[symbol].pop(prev_minute, None)
            if candle:
                asyncio.create_task(self._on_candle_close(symbol, prev_minute, candle))

        self.last_minute[symbol] = minute
        c = self.candles[symbol].get(minute)
        if not c:
            self.candles[symbol][minute] = {
                "open": price,
                "high": price,
                "low": price,
                "close": price,
                "volume": size
            }
        else:
            c["high"] = max(c["high"], price)
            c["low"] = min(c["low"], price)
            c["close"] = price
            c["volume"] += size

    async def _on_candle_close(self, symbol, minute_str, candle):
        symbol_clean = symbol.replace("-", "/")
        ts = make_aware(self._get_timestamp_obj(minute_str))

        raw_msg = {
            "T": "b",
            "t": ts.isoformat(),
            "o": candle["open"],
            "h": candle["high"],
            "l": candle["low"],
            "c": candle["close"],
            "v": candle["volume"],
            "S": symbol_clean
        }


        await dispatch_bar_message(raw_msg)

    async def _handle_message(self, msg):
        if msg.get("type") != "ticker":
            return
        symbol = msg.get("product_id")
        price = msg.get("price")
        size = msg.get("last_size")
        timestamp = msg.get("time")
        if symbol and price and size and timestamp:
            self._update_candle(symbol, price, size, timestamp)
        self.live_prices[symbol.replace("-", "")] = float(price)

    async def start(self):
        while True:
            try:
                async with websockets.connect(URI, ping_interval=None) as ws:
                    await self._subscribe(ws)
                    async for message in ws:
                        msg = json.loads(message)
                        await self._handle_message(msg)
            except Exception as e:
                print(f"❌ WebSocket error: {e}")
                await asyncio.sleep(3)

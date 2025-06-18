import asyncio
import websockets
import json
from django.db import close_old_connections
from asgiref.sync import sync_to_async
from core.models.symbol import Symbol
from streaming.websocket.dispatcher import dispatch_bar_message

# 🔐 Claves Alpaca (usa las reales con precaución)
API_KEY = "PKALPV6774BZYC8TQ29Q"
API_SECRET = "tUczQ1yDfIQMQzXubtwmpBFiJj8JNZhkMc8gYQaT"

# 🌐 URLs
IEX_URL = "wss://stream.data.alpaca.markets/v2/iex"
CRYPTO_URL = "wss://stream.data.alpaca.markets/v1beta3/crypto/us"

# 🧪 Tickers configurados
STOCK_TICKERS = ["AAPL", "MSFT", "NVDA", "TSLA"]
CRYPTO_TICKERS = ["BTC/USD", "ETH/USD", "SOL/USD", "USDT/USD", "DOGE/USD", "LTC/USD", "TRUMP/USD", "AVAX/USD", "LINK/USD", "AAVE/USD"]

# Buffers
bar_queue = asyncio.Queue()
trade_queue = asyncio.Queue()

# 🌐 Conectores
async def connect_to_alpaca_stock():
    await connect_alpaca_ws(IEX_URL, STOCK_TICKERS, name="📈 IEX (Stocks)")

async def connect_to_alpaca_crypto():
    await connect_alpaca_ws(CRYPTO_URL, CRYPTO_TICKERS, name="💰 Crypto")

async def connect_alpaca_ws(url, tickers, name=""):
    while True:
        try:
            print(f"🌐 Conectando a {name}...")
            async with websockets.connect(url, ping_interval=None) as ws:
                # Autenticación
                await ws.send(json.dumps({
                    "action": "auth",
                    "key": API_KEY,
                    "secret": API_SECRET,
                }))


                await ws.send(json.dumps({
                    "action": "subscribe",
                    "bars": tickers,
                    "trades": tickers
                }))

                print(f"✅ Suscrito a {name}: {tickers}")


                async for message in ws:
                    data = json.loads(message)
                    for item in data:
                        if item.get("T") == "b":
                            await bar_queue.put(item)
                        elif item.get("T") == "t":
                            await trade_queue.put(item)

        except Exception as e:
            print(f"❌ Error en {name}: {e}")
            await asyncio.sleep(3)

# 📦 Worker para procesar velas (ya existente)
async def bar_worker():
    while True:
        bar = await bar_queue.get()
        try:
            await dispatch_bar_message(bar)
        except Exception as e:
            print(f"❌ Error procesando bar: {e}")

# 🆕 Worker para procesar precios por tick
async def trade_worker():
    while True:
        trade = await trade_queue.get()
        try:
            symbol_str = trade.get("S")
            price = trade.get("p")
            print(f"Updated price for: {symbol_str}: {price} ")
            if not symbol_str or price is None:
                continue
            await update_live_price(symbol_str, price)
        except Exception as e:
            print(f"❌ Error en trade_worker: {e}")

@sync_to_async
def update_live_price(symbol_str, price):
    close_old_connections()
    try:
        clean_symbol = symbol_str.replace("/", "")
        symbol = Symbol.objects.get(symbol=clean_symbol)
        symbol.live_price = price
        print(f"Updated price for: {symbol_str}: {price} " )
        symbol.save(update_fields=["live_price"])
    except Symbol.DoesNotExist:
        print(f"❌ Símbolo no encontrado: {symbol_str}")



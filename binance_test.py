import asyncio
import websockets
import json
import os

BINANCE_WS_URL = "wss://stream.binance.us:9443/stream"
TICKERS = ["btcusdt", "ethusdt", "solusdt"]

# Ej: "btcusdt" → "BTC/USDT"
SYMBOL_MAP = {t: t[:-4].upper() + "/USDT" for t in TICKERS}
prices = {}

def clear_console():
    os.system("cls" if os.name == "nt" else "clear")

def print_dashboard():
    clear_console()
    print("📊 LIVE CRYPTO PRICES (from Binance US)\n")
    for raw, display in SYMBOL_MAP.items():
        price = prices.get(display, "—")
        print(f"💰 {display}: {price} USD")

async def binance_price_dashboard():
    stream = "/".join([f"{s}@miniTicker" for s in TICKERS])
    url = f"{BINANCE_WS_URL}?streams={stream}"

    while True:
        try:
            print("🔌 Conectando a Binance US miniTicker...")
            async with websockets.connect(url, ping_interval=None) as ws:
                print("🟢 Conectado")

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    ticker_data = data.get("data", {})
                    symbol_raw = ticker_data.get("s", "").lower()  # ej: btcusdt
                    price = ticker_data.get("c")  # close

                    if symbol_raw in SYMBOL_MAP:
                        symbol = SYMBOL_MAP[symbol_raw]
                        prices[symbol] = f"{float(price):.2f}"
                        print_dashboard()

        except Exception as e:
            print("❌ Error:", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(binance_price_dashboard())

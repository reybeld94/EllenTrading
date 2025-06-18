import asyncio
import websockets
import json
import os

WS_URL = "wss://advanced-trade-ws.coinbase.com"
TICKERS = ["BTC-USD", "ETH-USD", "SOL-USD"]
prices = {}

def clear_console():
    os.system("cls" if os.name == "nt" else "clear")

def print_dashboard():
    clear_console()
    print("📊 LIVE CRYPTO PRICES (from Coinbase Advanced)\n")
    for symbol in TICKERS:
        price = prices.get(symbol, "—")
        print(f"💰 {symbol}: {price} USD")

async def coinbase_price_dashboard():
    while True:
        try:
            print("🔌 Conectando a Coinbase Advanced WebSocket...")
            async with websockets.connect(WS_URL, ping_interval=None) as ws:
                print("🟢 Conectado")

                await ws.send(json.dumps({
                    "type": "subscribe",
                    "channels": [
                        {
                            "name": "ticker",
                            "product_ids": TICKERS
                        }
                    ]
                }))
                print("📡 Suscripción enviada")

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
			
                    print("📩 Mensaje recibido:", data)

                    if data.get("type") == "ticker" and "price" in data:
                        symbol = data.get("product_id")
                        price = float(data["price"])
                        prices[symbol] = f"{price:.2f}"
                        print_dashboard()

        except Exception as e:
            print("❌ Error:", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(coinbase_price_dashboard())

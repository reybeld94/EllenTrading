import asyncio
import websockets
import json
import os

ALPACA_API_KEY = "PKALPV6774BZYC8TQ29Q"
ALPACA_SECRET = "tUczQ1yDfIQMQzXubtwmpBFiJj8JNZhkMc8gYQaT"
WS_URL = "wss://stream.data.alpaca.markets/v2/iex"
TICKERS = ["AAPL", "MSFT", "TSLA"]
prices = {}

def clear_console():
    os.system("cls" if os.name == "nt" else "clear")

def print_dashboard():
    clear_console()
    print("📊 LIVE STOCK PRICES (from Alpaca WebSocket)\n")
    for symbol in TICKERS:
        price = prices.get(symbol, "—")
        print(f"📈 {symbol}: {price} USD")

async def alpaca_ticker():
    while True:
        try:
            print(f"🔌 Conectando a {WS_URL}...")
            async with websockets.connect(WS_URL) as ws:
                print("🟢 Conectado")

                # AUTH
                auth_payload = {
                    "action": "auth",
                    "key": ALPACA_API_KEY,
                    "secret": ALPACA_SECRET
                }
                print("📤 Enviando auth:", auth_payload)
                await ws.send(json.dumps(auth_payload))

                auth_response = await ws.recv()
                print("📩 Respuesta de auth:", auth_response)

                # SUBSCRIPTION
                sub_payload = {
                    "action": "subscribe",
                    "trades": TICKERS
                }
                print("📤 Enviando suscripción:", sub_payload)
                await ws.send(json.dumps(sub_payload))

                sub_response = await ws.recv()
                print("📩 Respuesta de sub:", sub_response)

                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    for d in data:
                        if d.get("T") == "t":
                            symbol = d["S"]
                            price = d["p"]
                            prices[symbol] = f"{price:.2f}"
                            print_dashboard()

        except Exception as e:
            print("❌ Error:", e)
            await asyncio.sleep(5)

if __name__ == "__main__":
    asyncio.run(alpaca_ticker())

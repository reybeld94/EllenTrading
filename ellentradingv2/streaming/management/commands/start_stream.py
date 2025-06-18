from django.core.management.base import BaseCommand
from streaming.clients.alpaca_client import connect_to_alpaca_stock, bar_worker, trade_worker
from streaming.clients.coinbase_client import CoinbaseClient
from streaming.websocket.helpers import risk_loop
import asyncio

class Command(BaseCommand):
    help = "Initializing WebSocket stream connections"

    def handle(self, *args, **kwargs):
        print("🚀 Starting streaming services (Alpaca + Coinbase)...")

        async def run_all():
            coinbase_client = CoinbaseClient([
                "BTC-USD", "ETH-USD", "SOL-USD", "USDT-USD", "DOGE-USD",
                "LTC-USD", "TRUMP-USD", "AVAX-USD", "LINK-USD", "AAVE-USD",
                "DOT-USD", "XLM-USD", "TON-USD"
            ])

            await asyncio.gather(
                connect_to_alpaca_stock(),
                bar_worker(),
                trade_worker(),
                risk_loop(),
                coinbase_client.start(),
                coinbase_client.emit_live_prices_loop()
            )

        asyncio.run(run_all())

from channels.generic.websocket import AsyncWebsocketConsumer
from channels.generic.websocket import AsyncJsonWebsocketConsumer
import json

class MarketConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        # Extraer el ticker desde la URL (ej: /ws/market/AAPL/)
        self.ticker = self.scope["url_route"]["kwargs"]["ticker"]
        self.group_name = f"market_{self.ticker.lower()}"

        # Unirse al grupo del ticker
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        await self.send(text_data=json.dumps({
            'message': f'📡 Conectado al grupo {self.group_name}'
        }))

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        data = json.loads(text_data)
        print("Mensaje recibido desde frontend:", data)
        await self.send(text_data=json.dumps({"echo": data}))

    async def send_market_data(self, event):
        # Este método lo llama el dispatcher con `group_send`
        await self.send(text_data=json.dumps(event["data"]))

class SignalConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("signals", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("signals", self.channel_name)

    async def send_signal(self, event):
        await self.send(text_data=json.dumps(event["data"]))

class TradeConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("trades", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("trades", self.channel_name)

    async def send_trade(self, event):
        await self.send_json(event["data"])

class LivePriceConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("live_prices", self.channel_name)
        await self.accept()
        print("🧩 Cliente conectado a live_prices")

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("live_prices", self.channel_name)

    async def send_live_prices(self, event):
        await self.send(text_data=json.dumps(event["data"]))

class PortfolioConsumer(AsyncJsonWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("portfolio", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("portfolio", self.channel_name)

    async def send_portfolio(self, event):
        await self.send_json(event["data"])

class LogConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("log_stream", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("log_stream", self.channel_name)

    async def receive(self, text_data):
        pass  # opcional, no necesitamos recibir del cliente

    async def send_log(self, event):
        await self.send(text_data=json.dumps(event["log"]))
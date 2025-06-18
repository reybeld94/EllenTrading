# streaming/websocket/dispatcher.py

from core.validators.market import validate_bar_message
from core.models import MarketDataPoint
from core.models.symbol import Symbol
from channels.layers import get_channel_layer
from django.utils.timezone import make_aware, is_aware
from datetime import timedelta
from streaming.resampling.resample_symbol import resample_symbol_full
from django.db import close_old_connections
from asgiref.sync import sync_to_async, async_to_sync
import asyncio
import traceback
from streaming.websocket.helpers import emit_live_prices
from monitoring.utils import log_event


async def dispatch_bar_message(raw_msg: dict):
    close_old_connections()
    try:
        bar = validate_bar_message(raw_msg)
        if bar is None:
            await log_event(f"⚠️ Bar inválido (no pasó la validación): {raw_msg}", source="streaming", level="INFO")
            return
        symbol_str = bar["symbol"].replace("/", "")

        try:
            symbol_obj = await sync_to_async(Symbol.objects.get)(symbol=symbol_str)
        except Symbol.DoesNotExist:
            await log_event(f"❌ Symbol '{symbol_str}' no existe en DB. Bar: {bar}", source="streaming", level="ERROR")
            return

        # Guardar la vela de 1 minuto
        mdp, created = await sync_to_async(save_market_datapoint)(symbol_obj, bar)
        symbol_obj.live_price = bar["close"]
        await sync_to_async(symbol_obj.save)(update_fields=["live_price"])

        if created:
            sema = asyncio.Semaphore(10)

            async def limited_resample(symbol, tf, ts):
                async with sema:
                    await sync_to_async(resample_symbol_full)(symbol, base_tf="1m", target_tf=tf, timestamp_cierre=ts)

            for tf, mins in {"5m": 5, "15m": 15, "30m": 30, "1h": 60, "4h": 240}.items():
                if mdp.start_time.minute % mins == 0:
                    asyncio.create_task(limited_resample(symbol_obj, tf, mdp.start_time))

        await emit_market_data(symbol_obj, mdp)
        await emit_live_prices()

    except Exception as e:
        await log_event(f"❌ Error en dispatcher: {e}", source="streaming", level="ERROR")
        traceback.print_exc()


def save_market_datapoint(symbol_obj, bar):
    from django.db import transaction

    ts = bar["timestamp"]
    if not is_aware(ts):
        ts = make_aware(ts)

    async_to_sync(log_event)(f"📈 Nueva vela de 1m para: {symbol_obj}", source="streaming", level="INFO")

    with transaction.atomic():
        return MarketDataPoint.objects.update_or_create(
            symbol=symbol_obj,
            timeframe="1m",
            start_time=ts,
            defaults={
                "open": bar["open"],
                "high": bar["high"],
                "low": bar["low"],
                "close": bar["close"],
                "volume": bar["volume"],
                "normalized_volume": bar["normalized_volume"],
                "vwap": bar.get("vwap") or bar.get("vw"),
                "trade_count": bar.get("trade_count") or bar.get("n"),
                "exchange": bar.get("exchange") or bar.get("x"),
                "end_time": ts + timedelta(minutes=1),
                "is_closed": True,
            },
        )


async def emit_market_data(symbol_obj, mdp):
    channel_layer = get_channel_layer()
    group_name = f"market_{symbol_obj.symbol.replace('/', '')}"
    await channel_layer.group_send(
        group_name,
        {
            "type": "send_market_data",
            "data": {
                "ticker": symbol_obj.symbol,
                "timestamp": str(mdp.start_time),
                "open": mdp.open,
                "high": mdp.high,
                "low": mdp.low,
                "close": mdp.close,
                "volume": mdp.normalized_volume,
            },
        },
    )

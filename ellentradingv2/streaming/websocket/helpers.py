# streaming/websocket/helpers.py
import asyncio
from channels.layers import get_channel_layer
from asgiref.sync import sync_to_async
from trades.serializers import TradeSerializer
from core.models.symbol import Symbol
from trades.models.portfolio import Portfolio
from trades.models.trade import Trade
from trades.models.portfolio import Position
from django.db import close_old_connections
from monitoring.utils import log_event


def emit_signal(signal):
    close_old_connections()
    from asgiref.sync import async_to_sync
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        "signals",
        {
            "type": "send_signal",
            "data": {
                "id": signal.id,
                "received_at": signal.received_at.isoformat(),
                "symbol": signal.symbol.symbol,
                "direction": signal.signal,
                "strategy": signal.strategy.name,
                "confidence": signal.confidence_score,
                "status": signal.executed,
            }
        }
    )

async def emit_trade(trade):
    close_old_connections()
    channel_layer = get_channel_layer()
    data = TradeSerializer(trade).data
    data["ticker"] = trade.symbol.symbol

    await channel_layer.group_send("trades", {
        "type": "send_trade",
        "data": data
    })

    balance = await get_portfolio_balance()
    if balance is not None:
        await channel_layer.group_send("portfolio", {
            "type": "send_portfolio",
            "data": {"usd_balance": balance}
        })
    else:
        await log_event(f"Portafolio 'Simulado' no existe", source="backtest", level="ERROR")
        print("❌ Portafolio 'Simulado' no existe.")

async def emit_live_prices():
    close_old_connections()
    symbols = await sync_to_async(list)(Symbol.objects.filter(is_active=True))

    data = {
        symbol.symbol: symbol.live_price
        for symbol in symbols
        if symbol.live_price is not None
    }

    channel_layer = get_channel_layer()
    await channel_layer.group_send("live_prices", {
        "type": "send_live_prices",
        "data": data
    })

@sync_to_async
def get_portfolio_balance():
    close_old_connections()
    try:
        portfolio = Portfolio.objects.get(name="Simulado")
        return round(portfolio.usd_balance, 2)
    except Portfolio.DoesNotExist:
        return None


async def close_trade_async(trade, exit_price, pnl, reason):
    """
    Cierre de trade usando función centralizada (con import local para evitar circular)
    """
    from django.utils.timezone import now
    from trades.models.portfolio import Portfolio

    close_old_connections()

    try:
        # Import local para evitar circular import
        from trades.logic.trade_closer import close_trade_by_live_price

        # Usar la función centralizada
        result = close_trade_by_live_price(trade, exit_price, reason)

        if result["success"]:
            await log_event(
                f"✅ Trade #{trade.id} cerrado automáticamente: {reason} | PnL: ${result['pnl']:.2f}",
                source="streaming", level="INFO"
            )
        else:
            await log_event(
                f"❌ Error cerrando Trade #{trade.id}: {result['error']}",
                source="streaming", level="ERROR"
            )

        return result

    except Exception as e:
        # Fallback al método anterior si hay problemas
        await log_event(f"⚠️ Fallback a método anterior para Trade #{trade.id}: {e}", source="streaming",
                        level="WARNING")

        duration_sec = (now() - trade.executed_at).total_seconds()

        await log_event(
            f"Trade #{trade.id} Closed: Duration: {duration_sec:.1f} sec, Entry: {trade.price} → Exit: {exit_price} | PnL: {pnl:.2f} USD, Closed by live_price: {reason} at {exit_price}",
            source="strategy", level="INFO")

        trade.notes = (
                (trade.notes or "")
                + f"\n🔒 Closed by live_price: {reason} at {exit_price}"
                + f"\n⏱️ Duration: {duration_sec:.1f} sec"
                + f"\n💰 Entry: {trade.price} → Exit: {exit_price} | PnL: {pnl:.2f} USD"
        )

        trade.exit_price = exit_price
        trade.pnl = round(pnl, 2)
        trade.closed_at = now()
        trade.status = "CLOSED"

        await sync_to_async(trade.save)()

        # 🧩 Si era un BUY, hay que ajustar la posición
        if trade.direction.lower() == "buy":
            try:
                pos = await sync_to_async(Position.objects.get)(
                    portfolio__name="Simulado",
                    symbol=trade.symbol
                )
                pos.qty -= trade.quantity
                if pos.qty <= 0:
                    await sync_to_async(pos.delete)()
                    await log_event(f"Posicion eliminada para Trade #{trade.id}", source="streaming", level="INFO")
                else:
                    await sync_to_async(pos.save)(update_fields=["qty"])
                    await log_event(
                        f"Posicion actualizada para Trade #{trade.id} - {trade.symbol.symbol}, Cantidad: {pos.qty}",
                        source="streaming", level="INFO")
            except Position.DoesNotExist:
                await log_event(f"No se encontro posicion disponible para el Trade#{trade.id} - {trade.symbol.symbol}",
                                source="streaming", level="ERROR")

        try:
            portfolio = await sync_to_async(Portfolio.objects.get)(name="Simulado")
            usd_ganado = round(trade.quantity * exit_price, 2)
            portfolio.usd_balance += usd_ganado
            await sync_to_async(portfolio.save)(update_fields=["usd_balance"])
            await log_event(
                f"💸 Trade #{trade.id} - Balance actualizado: +${usd_ganado} → Nuevo balance: ${portfolio.usd_balance:.2f}",
                source="streaming", level="INFO")
        except Exception as e:
            await log_event(f"❌ Error actualizando balance al cerrar Trade#:{trade.id} ERROR: {e}", source="streaming",
                            level="ERROR")

        await emit_trade(trade)

async def analyze_trades_with_prices(prices):
    close_old_connections()

    trades = await sync_to_async(list)(
        Trade.objects.select_related("symbol").filter(status="EXECUTED")
    )

    for trade in trades:
        symbol = trade.symbol.symbol
        price = prices.get(symbol)
        if price is None:
            continue

        qty = trade.quantity or round(trade.notional / trade.price, 6)


        if trade.direction == "buy":
            pnl = (price - trade.price) * qty
            trade.min_price_seen = min(trade.min_price_seen or price, price)
            drawdown = (trade.price - trade.min_price_seen) * qty
        else:
            pnl = (trade.price - price) * qty
            trade.max_price_seen = max(trade.max_price_seen or price, price)
            drawdown = (trade.max_price_seen - trade.price) * qty

        trade.max_drawdown = max(trade.max_drawdown or 0, round(drawdown, 2))
        await sync_to_async(trade.save)(update_fields=["pnl", "max_drawdown", "min_price_seen", "max_price_seen"])

        # 🟡 Trailing Stop (con umbral mínimo)
        if trade.trailing_stop:
            entry_price = trade.price
            min_profit_before_trailing = 0.005  # 0.5% mínimo de ganancia antes de activar trailing
            current_gain = (price - entry_price) / entry_price

            if current_gain >= min_profit_before_trailing:
                if not trade.highest_price or \
                   (trade.direction == "buy" and price > trade.highest_price) or \
                   (trade.direction == "sell" and price < trade.highest_price):
                    trade.highest_price = price
                    await sync_to_async(trade.save)(update_fields=["highest_price"])

                if trade.trailing_stop_level:
                    if (trade.direction == "buy" and price <= trade.trailing_stop_level) or \
                       (trade.direction == "sell" and price >= trade.trailing_stop_level):
                        return await close_trade_async(trade, price, pnl, "Trailing Stop Hit")

        # 🔴 Stop Loss
        if trade.stop_loss:
            if (trade.direction == "buy" and price <= trade.stop_loss) or \
               (trade.direction == "sell" and price >= trade.stop_loss):
                return await close_trade_async(trade, price, pnl, "Stop Loss Hit")

        # 🟢 Take Profit
        if trade.take_profit:
            if (trade.direction == "buy" and price >= trade.take_profit) or \
               (trade.direction == "sell" and price <= trade.take_profit):
                return await close_trade_async(trade, price, pnl, "Take Profit Hit")

        # 🧾 Actualizar solo PnL si no se cerró
        trade.pnl = round(pnl, 2)
        await sync_to_async(trade.save)(update_fields=["pnl"])
        await emit_trade(trade)

async def risk_loop():
    while True:
        await asyncio.sleep(2)  # Cada 2 segundos
        try:
            symbols = await sync_to_async(list)(Symbol.objects.filter(is_active=True))
            data = {
                s.symbol: s.live_price
                for s in symbols
                if s.live_price is not None
            }
            await analyze_trades_with_prices(data)
        except Exception as e:
            await log_event(f"Error en risk loop: {e}", source="streaming", level="ERROR")

@sync_to_async
def update_live_prices_bulk(price_dict):
    from django.db import close_old_connections
    close_old_connections()
    for symbol_str, price in price_dict.items():
        try:
            symbol = Symbol.objects.get(symbol=symbol_str)
            symbol.live_price = price
            symbol.save(update_fields=["live_price"])
        except Symbol.DoesNotExist:
            continue

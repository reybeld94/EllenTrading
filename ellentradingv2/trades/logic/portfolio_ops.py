from datetime import datetime
from trades.models.portfolio import Portfolio, Position
from core.models.symbol import Symbol
from asgiref.sync import async_to_sync
from monitoring.utils import log_event
from trades.models.trade import Trade
from streaming.websocket.helpers import emit_trade
from django.utils.timezone import now
from trades.logic.trade_closer import close_trades_by_sell_position

def buy_position(portfolio_name: str, symbol_str: str, amount_usd: float):
    portfolio = Portfolio.objects.get(name=portfolio_name)

    symbol = Symbol.objects.get(symbol=symbol_str)
    price = symbol.live_price

    qty = round(amount_usd / price, 6)

    position, _ = Position.objects.get_or_create(portfolio=portfolio, symbol=symbol)

    new_qty = position.qty + qty
    new_avg_price = (
        (position.qty * position.avg_price) + (qty * price)
    ) / new_qty if new_qty else price

    position.qty = new_qty
    position.avg_price = new_avg_price
    position.last_buy = datetime.utcnow()
    position.save()

    portfolio.usd_balance -= amount_usd
    portfolio.save()

    async_to_sync(log_event)(f"✅ Simulated BUY: {qty} {symbol_str} @ ${price:.2f}", source='trades', level='INFO')


def sell_position(portfolio_name: str, symbol_str: str, percent: float = 100):
    """
    Vende posición usando la función centralizada de cierre
    """
    portfolio = Portfolio.objects.get(name=portfolio_name)
    symbol = Symbol.objects.get(symbol=symbol_str)
    position = Position.objects.filter(portfolio=portfolio, symbol=symbol).first()

    if not position or position.qty <= 0:
        async_to_sync(log_event)(f"❌ No hay cantidad disponible para vender: {symbol.name}",
                                 source='trades', level='ERROR')
        raise ValueError("❌ No hay cantidad disponible para vender")

    price = symbol.live_price
    if not price or price <= 0:
        async_to_sync(log_event)(f"❌ Precio inválido para {symbol_str}: {price}",
                                 source='trades', level='ERROR')
        raise ValueError(f"❌ Precio inválido para {symbol_str}: {price}")

    # Buscar trades BUY ejecutados para cerrar (solo los rentables)
    open_buys = Trade.objects.filter(
        symbol=symbol,
        status="EXECUTED",
        direction="buy"
    ).order_by("executed_at")

    # Filtrar solo trades rentables
    profitable_trades = []
    for trade in open_buys:
        pnl = (price - trade.price) * trade.quantity
        if pnl > 0:
            profitable_trades.append(trade)
        else:
            async_to_sync(log_event)(f"⚠️ Trade# {trade.id} ignorado (PnL negativo: {pnl:.2f})",
                                     source='trades', level='INFO')

    if not profitable_trades:
        async_to_sync(log_event)("⚠️ Ningún trade en ganancia fue encontrado. Abortando venta.",
                                 source='trades', level='INFO')
        return

    # Usar función centralizada para cerrar todos los trades rentables
    result = close_trades_by_sell_position(symbol, price, profitable_trades)

    if result["success"]:
        async_to_sync(log_event)(
            f"✅ SELL POSITION completado: {result['trades_closed']} trades | PnL: ${result['total_pnl']:.2f}",
            source='trades', level='INFO'
        )
    else:
        async_to_sync(log_event)(
            f"❌ Error en SELL POSITION: {result.get('error', 'Unknown error')}",
            source='trades', level='ERROR'
        )

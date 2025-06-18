# trades/logic/trade_closer.py - VERSIÓN CORREGIDA (sin import circular)
"""
🎯 FUNCIÓN CENTRALIZADA PARA CERRAR TRADES
Resuelve todos los problemas de inconsistencia en balance y posiciones
"""

from django.utils.timezone import now
from django.db import transaction, close_old_connections
from asgiref.sync import async_to_sync, sync_to_async
from trades.models.trade import Trade
from trades.models.portfolio import Portfolio, Position
from monitoring.utils import log_event
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Dict, Any


@transaction.atomic
def close_trade_unified(
        trade_id: int,
        exit_price: float,
        reason: str,
        close_type: str = "auto",  # "auto", "manual", "stop_loss", "take_profit", "trailing"
        portfolio_name: str = "Simulado"
) -> Dict[str, Any]:
    """
    🎯 FUNCIÓN CENTRALIZADA PARA CERRAR TRADES
    Reemplaza todas las funciones de cierre dispersas

    Args:
        trade_id: ID del trade a cerrar
        exit_price: Precio de salida
        reason: Razón del cierre
        close_type: Tipo de cierre
        portfolio_name: Nombre del portfolio

    Returns:
        Dict con resultado del cierre
    """
    try:
        close_old_connections()

        # 1. 🔍 VALIDAR TRADE
        try:
            trade = Trade.objects.select_related('symbol').get(id=trade_id)
        except Trade.DoesNotExist:
            return {"success": False, "error": f"Trade {trade_id} no existe"}

        if trade.status != "EXECUTED":
            return {
                "success": False,
                "error": f"Trade {trade_id} no está EXECUTED (status: {trade.status})"
            }

        if exit_price <= 0:
            return {"success": False, "error": f"Precio de salida inválido: {exit_price}"}

        # 2. 📊 CALCULAR MÉTRICAS
        duration_sec = (now() - trade.executed_at).total_seconds()

        if trade.direction.lower() == "buy":
            pnl = (exit_price - trade.price) * trade.quantity
            usd_recovered = trade.quantity * exit_price  # Lo que recuperamos de la venta
        else:  # sell
            pnl = (trade.price - exit_price) * trade.quantity
            usd_recovered = 0  # En SELLs no recuperamos USD, ya estaba vendido

        pnl = round(pnl, 2)

        # 3. 📝 ACTUALIZAR TRADE
        trade.exit_price = exit_price
        trade.pnl = pnl
        trade.closed_at = now()
        trade.status = "CLOSED"
        trade.notes = (trade.notes or "") + f"\n🔒 Closed by {close_type}: {reason}"
        trade.notes += f"\n⏱️ Duration: {duration_sec:.1f} sec"
        trade.notes += f"\n💰 Entry: {trade.price} → Exit: {exit_price} | PnL: {pnl:.2f} USD"
        trade.save()

        # 4. 🏛️ ACTUALIZAR POSITION (solo para BUY trades)
        position_updated = False
        if trade.direction.lower() == "buy":
            try:
                position = Position.objects.get(
                    portfolio__name=portfolio_name,
                    symbol=trade.symbol
                )

                # Verificar que tenemos suficiente cantidad
                if position.qty >= trade.quantity:
                    position.qty -= trade.quantity
                    if position.qty <= 0:
                        position.delete()
                        async_to_sync(log_event)(
                            f"🗑️ Position eliminada para {trade.symbol.symbol}",
                            source="trade_closer", level="INFO"
                        )
                    else:
                        position.save(update_fields=["qty"])
                        async_to_sync(log_event)(
                            f"📉 Position actualizada: {trade.symbol.symbol} qty={position.qty}",
                            source="trade_closer", level="INFO"
                        )
                    position_updated = True
                else:
                    async_to_sync(log_event)(
                        f"⚠️ INCONSISTENCIA: Position qty ({position.qty}) < Trade qty ({trade.quantity})",
                        source="trade_closer", level="WARNING"
                    )

            except Position.DoesNotExist:
                async_to_sync(log_event)(
                    f"⚠️ INCONSISTENCIA: No existe Position para Trade #{trade_id}",
                    source="trade_closer", level="WARNING"
                )

        # 5. 💰 ACTUALIZAR PORTFOLIO BALANCE
        balance_updated = False
        new_balance = 0

        try:
            portfolio = Portfolio.objects.get(name=portfolio_name)

            if trade.direction.lower() == "buy":
                # En BUY: recuperamos el USD de la venta
                portfolio.usd_balance += usd_recovered
                balance_change = f"+${usd_recovered:.2f}"
            else:
                # En SELL: ya teníamos el USD, no hay cambio de balance
                balance_change = "$0.00 (SELL trade)"

            new_balance = portfolio.usd_balance
            portfolio.save(update_fields=["usd_balance"])
            balance_updated = True

            async_to_sync(log_event)(
                f"💸 Trade #{trade.id} closed: {balance_change} → Balance: ${new_balance:.2f}",
                source="trade_closer", level="INFO"
            )

        except Portfolio.DoesNotExist:
            async_to_sync(log_event)(
                f"❌ Portfolio '{portfolio_name}' no existe",
                source="trade_closer", level="ERROR"
            )

        # 6. 📡 EMITIR WEBSOCKET (import local para evitar circular)
        try:
            from streaming.websocket.helpers import emit_trade
            async_to_sync(emit_trade)(trade)
        except ImportError:
            # Fallback si hay problemas de import
            async_to_sync(log_event)(
                f"⚠️ No se pudo emitir WebSocket para Trade #{trade.id}",
                source="trade_closer", level="WARNING"
            )

        # 7. 📋 LOG FINAL
        async_to_sync(log_event)(
            f"✅ Trade #{trade.id} CERRADO: {trade.symbol.symbol} {trade.direction.upper()} "
            f"| Entry: ${trade.price:.4f} → Exit: ${exit_price:.4f} "
            f"| PnL: ${pnl:.2f} | Duration: {duration_sec:.1f}s | Reason: {reason}",
            source="trade_closer", level="INFO"
        )

        return {
            "success": True,
            "trade_id": trade.id,
            "symbol": trade.symbol.symbol,
            "direction": trade.direction,
            "entry_price": trade.price,
            "exit_price": exit_price,
            "pnl": pnl,
            "duration_sec": duration_sec,
            "position_updated": position_updated,
            "balance_updated": balance_updated,
            "new_balance": new_balance,
            "reason": reason,
            "close_type": close_type
        }

    except Exception as e:
        async_to_sync(log_event)(
            f"❌ ERROR CRÍTICO cerrando Trade #{trade_id}: {e}",
            source='trade_closer', level='ERROR'
        )
        return {
            "success": False,
            "error": str(e),
            "trade_id": trade_id
        }


# 🔧 FUNCIONES AUXILIARES PARA MIGRACIÓN GRADUAL

def close_trade_by_live_price(trade, exit_price, reason):
    """
    Wrapper para compatibilidad con el sistema actual de live prices
    """
    return close_trade_unified(
        trade_id=trade.id,
        exit_price=exit_price,
        reason=reason,
        close_type="auto_live_price"
    )


def close_trade_manually_unified(trade_id, current_price=None):
    """
    Wrapper para cierre manual desde views
    """
    try:
        trade = Trade.objects.get(id=trade_id, status="EXECUTED")
        exit_price = current_price or trade.symbol.live_price or trade.price

        return close_trade_unified(
            trade_id=trade_id,
            exit_price=exit_price,
            reason="Manual close by user",
            close_type="manual"
        )
    except Trade.DoesNotExist:
        return {"success": False, "error": f"Trade {trade_id} no encontrado"}


def close_trades_by_sell_position(symbol, price, trades_to_close):
    """
    Wrapper para cerrar múltiples trades (sell_position)
    """
    results = []
    total_closed = 0
    total_pnl = 0

    for trade in trades_to_close:
        result = close_trade_unified(
            trade_id=trade.id,
            exit_price=price,
            reason=f"Closed by sell_position at ${price:.4f}",
            close_type="sell_position"
        )

        if result["success"]:
            total_closed += 1
            total_pnl += result["pnl"]

        results.append(result)

    async_to_sync(log_event)(
        f"🔄 SELL POSITION completado: {total_closed} trades cerrados | PnL total: ${total_pnl:.2f}",
        source="trade_closer", level="INFO"
    )

    return {
        "success": True,
        "trades_closed": total_closed,
        "total_pnl": total_pnl,
        "results": results
    }
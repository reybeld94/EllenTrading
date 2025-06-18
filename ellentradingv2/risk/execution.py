from django.utils.timezone import now
from risk.utils import generate_exit_parameters
from trades.models.trade import Trade
from trades.models.portfolio import Position, Portfolio
from trades.logic.portfolio_ops import buy_position, sell_position
from streaming.websocket.helpers import emit_trade
from monitoring.utils import log_event
from asgiref.sync import async_to_sync
from datetime import timedelta


def analyze_market_impact(symbol, size, direction):
    """
    Analiza el impacto potencial en el mercado de la ejecución
    """
    try:
        # Analizar trades recientes del símbolo para estimar impact
        recent_trades = Trade.objects.filter(
            symbol=symbol,
            executed_at__gte=now() - timedelta(hours=24),
            status__in=["EXECUTED", "CLOSED"]
        )

        if recent_trades.count() < 3:
            return {
                "impact_level": "low",
                "suggested_split": 1,
                "timing_delay": 0
            }

        # Calcular volumen promedio y size relativo
        recent_sizes = []
        for trade in recent_trades:
            if trade.notional:
                recent_sizes.append(trade.notional)
            elif trade.quantity and symbol.live_price:
                recent_sizes.append(trade.quantity * symbol.live_price)

        if not recent_sizes:
            return {"impact_level": "low", "suggested_split": 1, "timing_delay": 0}

        avg_size = sum(recent_sizes) / len(recent_sizes)
        size_ratio = size / avg_size if avg_size > 0 else 1

        # Determinar impacto
        if size_ratio > 3:
            return {
                "impact_level": "high",
                "suggested_split": 3,
                "timing_delay": 30  # 30 seconds between orders
            }
        elif size_ratio > 1.5:
            return {
                "impact_level": "medium",
                "suggested_split": 2,
                "timing_delay": 15
            }
        else:
            return {
                "impact_level": "low",
                "suggested_split": 1,
                "timing_delay": 0
            }

    except Exception as e:
        async_to_sync(log_event)(f"Error analyzing market impact: {e}", source='execution', level='ERROR')
        return {"impact_level": "low", "suggested_split": 1, "timing_delay": 0}


def optimize_execution_timing(signal, direction):
    """
    Optimiza el timing de ejecución basado en condiciones del mercado
    """
    try:
        current_time = now()
        hour = current_time.hour
        minute = current_time.minute

        # Market timing factors
        timing_score = 1.0
        timing_reason = "optimal"

        # Market hours optimization
        if 9 <= hour <= 16:  # Market hours
            if hour == 9 and minute < 30:  # Opening 30 min
                timing_score = 0.8
                timing_reason = "market_opening"
            elif hour == 16 and minute > 30:  # Closing 30 min
                timing_score = 0.9
                timing_reason = "market_closing"
            else:
                timing_score = 1.1
                timing_reason = "market_hours"
        else:  # After hours
            timing_score = 0.7
            timing_reason = "after_hours"

        # Signal freshness
        signal_age = (current_time - signal.received_at).total_seconds() / 60
        if signal_age < 2:
            timing_score *= 1.1  # Very fresh signal
        elif signal_age > 15:
            timing_score *= 0.9  # Aging signal

        return {
            "timing_score": timing_score,
            "timing_reason": timing_reason,
            "should_delay": timing_score < 0.8,
            "delay_minutes": max(0, (0.8 - timing_score) * 10) if timing_score < 0.8 else 0
        }

    except Exception as e:
        async_to_sync(log_event)(f"Error optimizing timing: {e}", source='execution', level='ERROR')
        return {"timing_score": 1.0, "timing_reason": "default", "should_delay": False, "delay_minutes": 0}


def calculate_slippage_estimate(symbol, size, direction):
    """
    Estima el slippage esperado para la ejecución
    """
    try:
        # Análisis básico de slippage basado en volatilidad reciente
        recent_trades = Trade.objects.filter(
            symbol=symbol,
            executed_at__gte=now() - timedelta(hours=6),
            status__in=["EXECUTED", "CLOSED"]
        )

        if recent_trades.count() < 2:
            return 0.001  # 0.1% default slippage

        # Calcular volatilidad de precios
        prices = []
        for trade in recent_trades:
            if trade.price:
                prices.append(trade.price)

        if len(prices) < 2:
            return 0.001

        # Volatilidad simple
        price_changes = [abs(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
        avg_volatility = sum(price_changes) / len(price_changes) if price_changes else 0.001

        # Ajustar por tamaño de orden
        base_slippage = avg_volatility * 0.5  # 50% of volatility as base slippage

        # Size impact
        if symbol.asset_class == "crypto":
            size_factor = min(size / 10000, 0.5)  # Cap at 0.5% additional
        else:
            size_factor = min(size / 50000, 0.3)  # Cap at 0.3% additional

        total_slippage = base_slippage + size_factor
        return min(total_slippage, 0.02)  # Cap total slippage at 2%

    except Exception as e:
        async_to_sync(log_event)(f"Error calculating slippage: {e}", source='execution', level='ERROR')
        return 0.001


def validate_pre_execution(signal, direction, size, config):
    """
    Validaciones finales antes de ejecutar el trade
    """
    try:
        validations = {
            "portfolio_checks": True,
            "risk_limits": True,
            "market_conditions": True,
            "signal_quality": True,
            "timing": True
        }

        issues = []

        # 1. Portfolio health check
        try:
            portfolio = Portfolio.objects.get(name="Simulado")
            if portfolio.usd_balance < size:
                validations["portfolio_checks"] = False
                issues.append("Insufficient balance")
        except Exception:
            validations["portfolio_checks"] = False
            issues.append("Portfolio not found")

        # 2. Risk limits check
        active_trades = Trade.objects.filter(status="EXECUTED").count()
        if active_trades >= config.get("max_positions", 8):
            validations["risk_limits"] = False
            issues.append("Max positions reached")

        # 3. Signal quality recheck
        if signal.confidence_score < 30:
            validations["signal_quality"] = False
            issues.append("Signal confidence too low")

        # 4. Market timing
        timing_info = optimize_execution_timing(signal, direction)
        if timing_info["should_delay"]:
            validations["timing"] = False
            issues.append(f"Poor timing: {timing_info['timing_reason']}")

        all_valid = all(validations.values())

        return {
            "valid": all_valid,
            "validations": validations,
            "issues": issues,
            "timing_info": timing_info
        }

    except Exception as e:
        async_to_sync(log_event)(f"Error in pre-execution validation: {e}", source='execution', level='ERROR')
        return {
            "valid": False,
            "validations": {},
            "issues": ["Validation error"],
            "timing_info": {}
        }


def execute_simulated_trade(signal, direction, size, config):
    """
    Ejecución simulada mejorada con análisis avanzado
    """
    try:
        # Pre-execution validation
        validation_result = validate_pre_execution(signal, direction, size, config)

        if not validation_result["valid"]:
            async_to_sync(log_event)(
                f"❌ Trade blocked by validation: {', '.join(validation_result['issues'])}",
                source='execution', level='WARNING'
            )
            return None

        # Get current price with slippage consideration
        base_price = signal.symbol.live_price
        estimated_slippage = calculate_slippage_estimate(signal.symbol, size, direction)

        # Apply slippage
        if direction.lower() == "buy":
            execution_price = base_price * (1 + estimated_slippage)
        else:
            execution_price = base_price * (1 - estimated_slippage)

        # Market impact analysis
        impact_analysis = analyze_market_impact(signal.symbol, size, direction)

        async_to_sync(log_event)(
            f"📊 Execution analysis: slippage={estimated_slippage:.3%}, "
            f"impact={impact_analysis['impact_level']}, "
            f"timing_score={validation_result['timing_info'].get('timing_score', 1.0):.2f}",
            source='execution', level='INFO'
        )

        # Execute the portfolio operation
        if direction.lower() == "buy":
            async_to_sync(log_event)("🔄 Executing BUY position...", source='execution', level='INFO')
            buy_position("Simulado", signal.symbol.symbol, size)
            notional = size
            qty = round(size / execution_price, 6)
        else:
            try:
                async_to_sync(log_event)("🔄 Executing SELL position...", source='execution', level='INFO')
                sell_position("Simulado", signal.symbol.symbol)
                async_to_sync(log_event)("🛑 SELL realizado como cierre de posiciones BUY.", source='execution',
                                         level='INFO')
                return None
            except ValueError as e:
                async_to_sync(log_event)(f"❌ SELL abortado: {e}", source='execution', level='ERROR')
                return None

    except Exception as e:
        async_to_sync(log_event)(f"❌ Error en ejecución de portfolio: {e}", source='execution', level='ERROR')
        return None

    # Generate enhanced exit parameters
    try:
        exit_params = generate_exit_parameters(execution_price, direction, config=config)
    except Exception as e:
        async_to_sync(log_event)(f"❌ Error generando exit parameters: {e}", source='execution', level='ERROR')
        # Fallback exit parameters
        exit_params = {
            "stop_loss": execution_price * 0.98 if direction.lower() == "buy" else execution_price * 1.02,
            "take_profit": execution_price * 1.05 if direction.lower() == "buy" else execution_price * 0.95,
            "trailing_stop": 0.01,
            "trailing_level": execution_price
        }

    # Create comprehensive trade data
    trade_data = {
        "symbol": signal.symbol,
        "direction": direction.lower(),
        "price": execution_price,
        "execution_mode": "simulated",
        "confidence_score": int(signal.confidence_score),
        "strategy": signal.strategy.name if signal.strategy else None,
        "notes": f"Enhanced execution: slippage={estimated_slippage:.3%}, impact={impact_analysis['impact_level']}",
        "status": "EXECUTED",
        "executed_at": now(),
        "quantity": qty,
        "filled_quantity": qty,
        "notional": notional,
        "filled_notional": notional,

        # Enhanced metadata
        "estimated_slippage": round(estimated_slippage * 100, 3),  # Store as percentage
        "market_impact": impact_analysis['impact_level'],
        "execution_quality": validation_result['timing_info'].get('timing_score', 1.0),
    }

    # Add exit parameters
    trade_data.update(exit_params)

    try:
        # Create trade record
        trade = Trade.objects.create(**trade_data)
        trade.triggered_by.add(signal)

        # Enhanced logging
        async_to_sync(log_event)(
            f"✅ Trade #{trade.id} ejecutado exitosamente: "
            f"{trade.symbol.symbol} {direction.upper()} @ ${execution_price:.4f} "
            f"(qty: {qty:.6f}, notional: ${notional:.2f})",
            source='execution', level='INFO'
        )

        async_to_sync(log_event)(
            f"🎯 Exit targets: SL=${exit_params['stop_loss']:.4f}, "
            f"TP=${exit_params['take_profit']:.4f}, "
            f"Trail={exit_params['trailing_stop']:.2%}",
            source='execution', level='INFO'
        )

        # Emit trade to WebSocket
        async_to_sync(emit_trade)(trade)

        # Post-execution analytics
        portfolio = Portfolio.objects.get(name="Simulado")
        remaining_balance = portfolio.usd_balance
        position_size_pct = (notional / (remaining_balance + notional)) * 100

        async_to_sync(log_event)(
            f"📈 Portfolio update: remaining=${remaining_balance:.2f}, "
            f"position_size={position_size_pct:.1f}% of capital",
            source='execution', level='INFO'
        )

        return trade

    except Exception as e:
        async_to_sync(log_event)(f"❌ Error creando trade record: {e}", source='execution', level='ERROR')
        return None
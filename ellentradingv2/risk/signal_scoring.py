from datetime import timedelta
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


def weighted_score(signal, config):
    """
    Calcula score ponderado optimizado para rangos universales 30-100
    """
    prio_weights = config["strategy_weights"]
    conf_weight = 0.7  # Más peso a confidence (era 0.6)
    score_weight = 1 - conf_weight

    prio = signal.strategy.priority.title() if signal.strategy else "Confirm"

    if prio not in prio_weights:
        async_to_sync(log_event)(f"❌ Prioridad '{prio}' no está definida en strategy_weights: {prio_weights}",
                                 source='risk_manager', level='ERROR')
        raise ValueError(f"❌ Prioridad '{prio}' no está definida en strategy_weights: {prio_weights}")

    weight = prio_weights[prio]
    conf = signal.confidence_score or 0
    strat_score = signal.strategy.score if signal.strategy and signal.strategy.score else 0

    # Optimización para rangos universales: normalizar confidence a 0-1
    normalized_conf = min(conf / 100.0, 1.0)
    normalized_strat = min(strat_score / 100.0, 1.0)

    return ((normalized_conf * weight * conf_weight) + (normalized_strat * score_weight)) * 100


def avg_weighted(signals, config):
    if not signals:
        return 0
    return sum(weighted_score(s, config) for s in signals) / len(signals)


def get_market_regime(bars):
    """
    Detecta régimen de mercado: Bull/Bear/Sideways
    """
    if len(bars) < 20:
        return "neutral"

    prices = [bar.close for bar in bars[-20:]]
    short_trend = (prices[-1] - prices[-5]) / prices[-5]
    medium_trend = (prices[-1] - prices[-15]) / prices[-15]

    # Volatilidad
    price_changes = [abs(prices[i] - prices[i - 1]) / prices[i - 1] for i in range(1, len(prices))]
    volatility = sum(price_changes) / len(price_changes)

    if medium_trend > 0.03 and short_trend > 0.01:
        return "bull"
    elif medium_trend < -0.03 and short_trend < -0.01:
        return "bear"
    elif volatility < 0.015:  # Low volatility
        return "sideways"
    else:
        return "neutral"


def evaluate_categorized(categorized, direction, config):
    """
    Evalúa si las señales tienen el peso suficiente para justificar un trade.
    OPTIMIZADO para rangos universales 30-100
    """

    # ===== REGLAS GENERALES OPTIMIZADAS =====

    # REGLA 1: PRIMARY fuerte ejecuta sola (threshold optimizado)
    if categorized["Primary"]:
        best = max(categorized["Primary"], key=lambda s: weighted_score(s, config))
        best_score = weighted_score(best, config)
        if best_score >= config.get("primary_min_score", 45):  # Era 50, ahora 45
            async_to_sync(log_event)("✅ Trade aprobado: Primary fuerte", source='risk_manager', level='INFO')
            return {
                "approved": True,
                "action": direction,
                "reason": f"Primary '{best.strategy.name}' approved with score {best_score:.2f}",
                "signal": best
            }

    # REGLA 2: CONTEXT + CONFIRM con promedio decente (threshold optimizado)
    if categorized["Context"] and categorized["Confirm"]:
        combined = categorized["Context"] + categorized["Confirm"]
        if len(combined) >= 2:
            avg_score = avg_weighted(combined, config)
            if avg_score >= config.get("context_confirm_avg_score", 42):  # Era 50, ahora 42
                async_to_sync(log_event)("✅ Trade aprobado: Context + Confirm", source='risk_manager', level='INFO')
                return {
                    "approved": True,
                    "action": direction,
                    "reason": f"Context + Confirm aligned (avg score {avg_score:.2f})",
                    "signal": combined[0]
                }

    # REGLA 3: 3+ CONFIRM con buen score (threshold optimizado)
    if len(categorized["Confirm"]) >= 3:
        avg_score = avg_weighted(categorized["Confirm"], config)
        if avg_score >= config.get("confirm_min_avg_score", 40):  # Era 50, ahora 40
            async_to_sync(log_event)("✅ Trade aprobado: 3+ Confirm signals", source='risk_manager', level='INFO')
            return {
                "approved": True,
                "action": direction,
                "reason": f"3+ Confirm signals aligned (avg score {avg_score:.2f})",
                "signal": categorized["Confirm"][0]
            }

    # REGLA 4: 2+ PRIMARY con promedio alto (threshold optimizado)
    if len(categorized["Primary"]) >= 2:
        avg_score = avg_weighted(categorized["Primary"], config)
        if avg_score >= config.get("primary_group_avg_score", 48):  # Era 50, ahora 48
            async_to_sync(log_event)("✅ Trade aprobado: 2+ Primary aligned", source='risk_manager', level='INFO')
            return {
                "approved": True,
                "action": direction,
                "reason": f"2+ Primary strategies aligned (avg score {avg_score:.2f})",
                "signal": categorized["Primary"][0]
            }

    # ===== REGLAS CUSTOM MEJORADAS =====

    # CUSTOM 1: RSI + Engulfing + Volume (Más flexible)
    rsi = [s for s in categorized["Primary"] if s.strategy and s.strategy.name == "RSI Breakout Strategy"]
    be = [s for s in categorized["Confirm"] if s.strategy and s.strategy.name == "Bullish Engulfing Pattern"]
    vs = [s for s in categorized["Confirm"] if s.strategy and s.strategy.name == "Volume Spike"]

    if rsi and be and vs:
        combo = rsi + be + vs
        timestamps = [s.received_at for s in combo]
        if max(timestamps) - min(timestamps) <= timedelta(minutes=8):  # Era 5 min, ahora 8
            avg_score = avg_weighted(combo, config)
            if avg_score >= 60:  # Era 75, ahora 60
                async_to_sync(log_event)("✅ Trade aprobado: RSI + Engulfing + Volume", source='risk_manager',
                                         level='INFO')
                return {
                    "approved": True,
                    "action": direction,
                    "reason": f"Custom RSI combo (avg score {avg_score:.2f})",
                    "signal": combo[0]
                }

    # CUSTOM 2: Triple EMA + ADX (Más flexible)
    ema = [s for s in categorized["Primary"] if s.strategy and s.strategy.name == "Triple EMA Crossover Strategy"]
    adx = [s for s in categorized["Primary"] if s.strategy and s.strategy.name == "ADX Trend Strength Strategy"]

    if ema and adx:
        combo = ema + adx
        timestamps = [s.received_at for s in combo]
        if max(timestamps) - min(timestamps) <= timedelta(minutes=8):
            avg_score = avg_weighted(combo, config)
            if avg_score >= 55:  # Era 70, ahora 55
                async_to_sync(log_event)("✅ Trade aprobado: Triple EMA + ADX", source='risk_manager', level='INFO')
                return {
                    "approved": True,
                    "action": direction,
                    "reason": f"Custom EMA + ADX (avg score {avg_score:.2f})",
                    "signal": combo[0]
                }

    # CUSTOM 3: Bollinger + Volume (Más flexible)
    bb = [s for s in categorized["Primary"] if s.strategy and s.strategy.name == "Bollinger Band Breakout"]
    vs = [s for s in categorized["Confirm"] if s.strategy and s.strategy.name == "Volume Spike"]

    if bb and vs:
        combo = bb + vs
        timestamps = [s.received_at for s in combo]
        if max(timestamps) - min(timestamps) <= timedelta(minutes=8):
            avg_score = avg_weighted(combo, config)
            if avg_score >= 52:  # Era 72, ahora 52
                async_to_sync(log_event)("✅ Trade aprobado: Bollinger + Volume", source='risk_manager', level='INFO')
                return {
                    "approved": True,
                    "action": direction,
                    "reason": f"Custom Bollinger combo (avg score {avg_score:.2f})",
                    "signal": combo[0]
                }

    # CUSTOM 4: MACD + Ichimoku (Nueva combinación Primary + Context)
    macd = [s for s in categorized["Primary"] if s.strategy and s.strategy.name == "MACD Crossover Strategy"]
    ichimoku = [s for s in categorized["Context"] if s.strategy and s.strategy.name == "Ichimoku Cloud Breakout"]

    if macd and ichimoku:
        combo = macd + ichimoku
        timestamps = [s.received_at for s in combo]
        if max(timestamps) - min(timestamps) <= timedelta(minutes=8):
            avg_score = avg_weighted(combo, config)
            if avg_score >= 58:  # Era 75, ahora 58
                async_to_sync(log_event)("✅ Trade aprobado: MACD + Ichimoku", source='risk_manager', level='INFO')
                return {
                    "approved": True,
                    "action": direction,
                    "reason": f"Custom MACD + Ichimoku (avg score {avg_score:.2f})",
                    "signal": combo[0]
                }

    # CUSTOM 5: Donchian + Parabolic SAR (Nueva combinación de breakout)
    donchian = [s for s in categorized["Primary"] if s.strategy and s.strategy.name == "Donchian Channel Breakout"]
    psar = [s for s in categorized["Primary"] if s.strategy and s.strategy.name == "Parabolic SAR Trend Strategy"]

    if donchian and psar:
        combo = donchian + psar
        timestamps = [s.received_at for s in combo]
        if max(timestamps) - min(timestamps) <= timedelta(minutes=8):
            avg_score = avg_weighted(combo, config)
            if avg_score >= 60:
                async_to_sync(log_event)("✅ Trade aprobado: Donchian + PSAR", source='risk_manager', level='INFO')
                return {
                    "approved": True,
                    "action": direction,
                    "reason": f"Custom Breakout combo (avg score {avg_score:.2f})",
                    "signal": combo[0]
                }

    # CUSTOM 6: Fibonacci + Moving Average (Context + Primary)
    fib = [s for s in categorized["Context"] if s.strategy and s.strategy.name == "Fibonacci Retracement Strategy"]
    ma = [s for s in categorized["Primary"] if s.strategy and s.strategy.name == "Moving Average Cross Strategy"]

    if fib and ma:
        combo = fib + ma
        timestamps = [s.received_at for s in combo]
        if max(timestamps) - min(timestamps) <= timedelta(minutes=8):
            avg_score = avg_weighted(combo, config)
            if avg_score >= 55:
                async_to_sync(log_event)("✅ Trade aprobado: Fibonacci + MA", source='risk_manager', level='INFO')
                return {
                    "approved": True,
                    "action": direction,
                    "reason": f"Custom Fib + MA (avg score {avg_score:.2f})",
                    "signal": combo[0]
                }

    # CUSTOM 7: Cualquier 4+ señales con score decente (Nueva regla flexible)
    all_signals = categorized["Primary"] + categorized["Context"] + categorized["Confirm"]
    if len(all_signals) >= 4:
        timestamps = [s.received_at for s in all_signals]
        if max(timestamps) - min(timestamps) <= timedelta(minutes=10):  # Ventana más amplia
            avg_score = avg_weighted(all_signals, config)
            if avg_score >= 45:  # Score más bajo pero muchas señales
                async_to_sync(log_event)("✅ Trade aprobado: Múltiple confluencia", source='risk_manager', level='INFO')
                return {
                    "approved": True,
                    "action": direction,
                    "reason": f"Multiple signal confluence (avg score {avg_score:.2f})",
                    "signal": all_signals[0]
                }

    # ===== FINAL: No se aprueba =====
    async_to_sync(log_event)("❌ Trade no aprobado por scoring", source='risk_manager', level='INFO')
    return {
        "approved": False,
        "reason": f"Signals in '{direction}' direction do not meet optimized requirements"
    }
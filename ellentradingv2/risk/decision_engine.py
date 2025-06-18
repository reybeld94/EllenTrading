from collections import defaultdict
from core.models.enums import SignalType
from risk.utils import get_adjusted_confidence
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


def categorize_signals(signals):
    categorized = {
        "Primary": [],
        "Context": [],
        "Confirm": []
    }

    for s in signals:
        if not s.strategy:
            continue
        prio = s.strategy.priority.title()
        if prio in categorized:
            categorized[prio].append(s)

    return categorized


def group_signals_by_direction(signals, verbose=False):
    groups = defaultdict(list)
    if verbose:
        async_to_sync(log_event)("📦 Agrupando señales por dirección", source='risk_manager', level='INFO')
    for s in signals:
        if verbose:
            async_to_sync(log_event)(
                f"   • {s.symbol.symbol} | {s.signal} | {s.strategy.name if s.strategy else 'Sin estrategia'} | Conf: {s.confidence_score}",
                source='risk_manager', level='INFO')
        groups[s.signal.lower()].append(s)
    return groups


def has_consensus(signals):
    directions = set(s.signal for s in signals)
    return len(directions) == 1


def detect_market_regime(signals):
    """
    Detecta régimen de mercado basado en las señales activas
    """
    if not signals:
        return "neutral"

    # Analizar distribución de señales por prioridad
    primary_count = len([s for s in signals if s.strategy and s.strategy.priority.title() == "Primary"])
    context_count = len([s for s in signals if s.strategy and s.strategy.priority.title() == "Context"])
    confirm_count = len([s for s in signals if s.strategy and s.strategy.priority.title() == "Confirm"])

    total_signals = len(signals)

    # Analizar confidence promedio
    avg_confidence = sum(s.confidence_score or 0 for s in signals) / total_signals if total_signals > 0 else 0

    # Analizar momentum strategies
    momentum_strategies = ["RSI Breakout Strategy", "MACD Crossover Strategy", "Stochastic Oscillator"]
    momentum_signals = [s for s in signals if s.strategy and s.strategy.name in momentum_strategies]

    # Analizar trend strategies
    trend_strategies = ["ADX Trend Strength Strategy", "Triple EMA Crossover Strategy", "Moving Average Cross Strategy"]
    trend_signals = [s for s in signals if s.strategy and s.strategy.name in trend_strategies]

    # Clasificación de régimen
    if primary_count >= 3 and avg_confidence > 60:
        return "strong_trend"
    elif len(momentum_signals) > len(trend_signals) and avg_confidence > 50:
        return "momentum"
    elif len(trend_signals) >= 2 and avg_confidence > 45:
        return "trending"
    elif total_signals >= 4 and avg_confidence < 50:
        return "choppy"
    else:
        return "neutral"


def calculate_dynamic_weights(signals, config, market_regime):
    """
    Calcula pesos dinámicos basados en el régimen de mercado
    """
    base_weights = config["strategy_weights"].copy()

    if market_regime == "strong_trend":
        # En tendencias fuertes, dar más peso a Primary
        return {
            "Primary": base_weights["Primary"] * 1.3,
            "Context": base_weights["Context"] * 1.1,
            "Confirm": base_weights["Confirm"] * 0.9
        }
    elif market_regime == "momentum":
        # En momentum, balance entre Primary y Confirm
        return {
            "Primary": base_weights["Primary"] * 1.2,
            "Context": base_weights["Context"] * 0.9,
            "Confirm": base_weights["Confirm"] * 1.2
        }
    elif market_regime == "choppy":
        # En mercados choppy, ser más conservador
        return {
            "Primary": base_weights["Primary"] * 0.9,
            "Context": base_weights["Context"] * 1.1,
            "Confirm": base_weights["Confirm"] * 0.8
        }
    else:
        return base_weights


def determine_direction_from_conflict(signals, config, verbose=False):
    """
    Resolución de conflictos mejorada con pesos dinámicos y market regime
    """
    if not signals:
        return None, 0, 0

    # Detectar régimen de mercado
    market_regime = detect_market_regime(signals)

    # Calcular pesos dinámicos
    weights = calculate_dynamic_weights(signals, config, market_regime)

    if verbose:
        async_to_sync(log_event)(f"🎯 Market regime: {market_regime}", source='risk_manager', level='INFO')
        async_to_sync(log_event)(f"⚖️ Dynamic weights: {weights}", source='risk_manager', level='INFO')
        async_to_sync(log_event)("🧮 Calculando scores ponderados avanzados", source='risk_manager', level='INFO')

    buy_score = 0
    sell_score = 0

    # Factores de calidad adicionales
    strategy_diversity_bonus = 0
    timing_bonus = 0

    # Analizar diversidad de estrategias
    unique_strategies = set(s.strategy.name for s in signals if s.strategy)
    if len(unique_strategies) >= 3:
        strategy_diversity_bonus = 5
    elif len(unique_strategies) >= 2:
        strategy_diversity_bonus = 2

    # Analizar timing de señales (señales recientes tienen más peso)
    from django.utils.timezone import now
    current_time = now()

    for s in signals:
        prio = s.strategy.priority.title() if s.strategy else "Confirm"
        conf = get_adjusted_confidence(s)
        strat_score = s.strategy.score if s.strategy and s.strategy.score else 0
        weight = weights.get(prio, 0.5)

        # Normalizar confidence a rango 0-1 para cálculo más preciso
        normalized_conf = min(conf / 100.0, 1.0)
        normalized_strat = min(strat_score / 100.0, 1.0)

        # Score base mejorado
        base_score = (normalized_conf * 0.7 + normalized_strat * 0.3) * weight * 100

        # Bonus por timing (señales más recientes son mejores)
        signal_age_minutes = (current_time - s.received_at).total_seconds() / 60
        if signal_age_minutes <= 5:
            timing_bonus = 10
        elif signal_age_minutes <= 15:
            timing_bonus = 5
        elif signal_age_minutes <= 30:
            timing_bonus = 2
        else:
            timing_bonus = 0

        # Score final con bonificaciones
        total_score = base_score + strategy_diversity_bonus + timing_bonus

        if verbose:
            async_to_sync(log_event)(
                f"   • {s.symbol.symbol} | {s.signal} | {s.strategy.name if s.strategy else 'Sin estrategia'}",
                source='risk_manager', level='INFO')
            async_to_sync(log_event)(
                f"     → Prioridad: {prio} | Conf: {conf:.1f} | Score: {strat_score} | Peso: {weight:.2f}",
                source='risk_manager', level='INFO')
            async_to_sync(log_event)(
                f"     → Base: {base_score:.2f} | Timing+: {timing_bonus} | Diversity+: {strategy_diversity_bonus}",
                source='risk_manager', level='INFO')
            async_to_sync(log_event)(
                f"     → Score total: {total_score:.2f}",
                source='risk_manager', level='INFO')

        if s.signal.lower() == SignalType.BUY.lower():
            buy_score += total_score
        elif s.signal.lower() == SignalType.SELL.lower():
            sell_score += total_score

    # Threshold dinámico basado en market regime
    base_threshold = config.get("conflict_threshold", 15)  # Era 10, ahora 15

    if market_regime == "strong_trend":
        threshold = base_threshold * 0.8  # Más agresivo en tendencias fuertes
    elif market_regime == "choppy":
        threshold = base_threshold * 1.5  # Más conservador en mercados choppy
    elif market_regime == "momentum":
        threshold = base_threshold * 0.9  # Ligeramente más agresivo
    else:
        threshold = base_threshold

    if verbose:
        async_to_sync(log_event)(
            f"📊 Scores finales - BUY: {buy_score:.2f} / SELL: {sell_score:.2f}",
            source='risk_manager', level='INFO')
        async_to_sync(log_event)(
            f"⚖️ Threshold dinámico: {threshold:.1f} (régimen: {market_regime})",
            source='risk_manager', level='INFO')

    score_difference = abs(buy_score - sell_score)

    if score_difference < threshold:
        if verbose:
            async_to_sync(log_event)(
                f"⚖️ Diferencia {score_difference:.1f} < threshold {threshold:.1f} → Sin decisión",
                source='risk_manager', level='INFO')
        return None, buy_score, sell_score
    elif buy_score > sell_score:
        if verbose:
            async_to_sync(log_event)(
                f"🟢 BUY wins: {buy_score:.2f} vs {sell_score:.2f} (diff: {score_difference:.1f})",
                source='risk_manager', level='INFO')
        return "BUY", buy_score, sell_score
    elif sell_score > buy_score:
        if verbose:
            async_to_sync(log_event)(
                f"🔴 SELL wins: {sell_score:.2f} vs {buy_score:.2f} (diff: {score_difference:.1f})",
                source='risk_manager', level='INFO')
        return "SELL", buy_score, sell_score
    else:
        return None, buy_score, sell_score


def resolve_direction(signals, config, verbose=False):
    """
    Resolución de dirección mejorada con análisis de contexto
    """
    if verbose:
        async_to_sync(log_event)("🔍 Resolviendo dirección con análisis avanzado...", source='risk_manager',
                                 level='INFO')
        async_to_sync(log_event)(f"📡 Señales activas: {len(signals)}", source='risk_manager', level='INFO')

    if not signals:
        if verbose:
            async_to_sync(log_event)("❌ No hay señales activas", source='risk_manager', level='INFO')
        return None, [], "No active signals"

    # Verificar consenso simple primero
    if has_consensus(signals):
        direction = signals[0].signal
        if verbose:
            async_to_sync(log_event)(f"✅ Consenso detectado: {direction}", source='risk_manager', level='INFO')
        return direction, signals, "Perfect consensus among all signals"

    # Agrupar por dirección
    grouped = group_signals_by_direction(signals, verbose=verbose)

    # Si solo hay una dirección, usar esa
    if len(grouped) == 1:
        direction = list(grouped.keys())[0].upper()
        if verbose:
            async_to_sync(log_event)(f"✅ Una sola dirección: {direction}", source='risk_manager', level='INFO')
        return direction, grouped[direction.lower()], "Single direction signals"

    # Resolver conflicto con análisis avanzado
    direction, buy_score, sell_score = determine_direction_from_conflict(signals, config, verbose=verbose)

    if direction:
        filtered_signals = grouped.get(direction.lower(), [])
        market_regime = detect_market_regime(signals)

        if verbose:
            async_to_sync(log_event)(
                f"✅ Dirección resuelta: {direction} (régimen: {market_regime})",
                source='risk_manager', level='INFO')

        return direction, filtered_signals, f"Advanced resolution: BUY={buy_score:.2f} / SELL={sell_score:.2f} (regime: {market_regime})"

    if verbose:
        async_to_sync(log_event)("❌ No se pudo determinar dirección clara con análisis avanzado", source='risk_manager',
                                 level='INFO')

    return None, [], "No dominant direction could be determined with advanced analysis"
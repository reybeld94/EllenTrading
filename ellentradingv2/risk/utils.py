from django.utils.timezone import now
from datetime import timedelta
from django.utils import timezone
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


def generate_exit_parameters(price, direction, config=None):
    """
    Genera parámetros de salida mejorados con lógica adaptativa
    """
    if direction not in ["buy", "sell"]:
        raise ValueError(f"❌ Dirección inválida: {direction}")

    # Configuración por defecto mejorada
    default_config = {
        "sl_buffer_pct": 0.02,
        "tp_buffer_pct": 0.05,
        "trailing_stop_pct": 0.01,
        "enable_dynamic_exits": True
    }

    if config:
        default_config.update(config)

    config = default_config

    sl_pct = config["sl_buffer_pct"]
    tp_pct = config["tp_buffer_pct"]
    trail_pct = config["trailing_stop_pct"]

    # Dynamic adjustment based on price level
    if price > 1000:  # High-priced assets
        sl_pct *= 0.8  # Tighter stops
        tp_pct *= 0.8  # Tighter targets
    elif price < 10:  # Low-priced assets
        sl_pct *= 1.2  # Wider stops
        tp_pct *= 1.2  # Wider targets

    min_gap = max(0.05, price * 0.005)

    if direction == "buy":
        stop_loss = round(price * (1 - sl_pct), 5)
        take_profit = round(price * (1 + tp_pct), 5)
    else:  # SELL
        stop_loss = round(price * (1 + sl_pct), 5)
        take_profit = round(price * (1 - tp_pct), 5)

    # Verificación y corrección mejorada
    if direction == "buy":
        if stop_loss >= price:
            async_to_sync(log_event)(f"⚠️ Corrigiendo SL de BUY: {stop_loss} → {price - min_gap}",
                                     source='risk_manager', level='WARNING')
            stop_loss = round(price - min_gap, 5)
        if take_profit <= price:
            async_to_sync(log_event)(f"⚠️ Corrigiendo TP de BUY: {take_profit} → {price + min_gap}",
                                     source='risk_manager', level='WARNING')
            take_profit = round(price + min_gap, 5)
    else:  # SELL
        if stop_loss <= price:
            async_to_sync(log_event)(f"⚠️ Corrigiendo SL de SELL: {stop_loss} → {price + min_gap}",
                                     source='risk_manager', level='WARNING')
            stop_loss = round(price + min_gap, 5)
        if take_profit >= price:
            async_to_sync(log_event)(f"⚠️ Corrigiendo TP de SELL: {take_profit} → {price - min_gap}",
                                     source='risk_manager', level='WARNING')
            take_profit = round(price - min_gap, 5)

    # Trailing stop setup mejorado
    trailing_stop = trail_pct
    if direction == "buy":
        trailing_level = round(price + min_gap, 5)
    else:
        trailing_level = round(price - min_gap, 5)

    # Risk-to-reward validation
    if direction == "buy":
        risk = price - stop_loss
        reward = take_profit - price
    else:
        risk = stop_loss - price
        reward = price - take_profit

    risk_reward_ratio = reward / risk if risk > 0 else 0

    if risk_reward_ratio < 1.5:  # Poor risk-reward
        async_to_sync(log_event)(f"⚠️ Poor R:R ratio {risk_reward_ratio:.2f}, adjusting targets",
                                 source='risk_manager', level='WARNING')

        # Adjust take profit to improve R:R
        if direction == "buy":
            take_profit = price + (risk * 2.0)  # 2:1 R:R
        else:
            take_profit = price - (risk * 2.0)

    return {
        "stop_loss": stop_loss,
        "take_profit": take_profit,
        "trailing_stop": trailing_stop,
        "trailing_level": trailing_level,
        "risk_reward_ratio": risk_reward_ratio
    }


def get_adjusted_confidence(signal):
    """
    Calcula confidence ajustado con decay mejorado
    """
    try:
        age = (now() - signal.received_at).total_seconds() / 60
        duration = signal.strategy.validity_minutes if signal.strategy else 30

        # Decay curve mejorada
        if age <= duration * 0.5:  # First half: no decay
            decay = 1.0
        elif age <= duration:  # Second half: linear decay
            progress = (age - duration * 0.5) / (duration * 0.5)
            decay = 1.0 - (progress * 0.3)  # Max 30% decay
        else:  # Expired: sharp decay
            overtime = age - duration
            decay = 0.7 * (0.9 ** (overtime / 15))  # Exponential decay every 15 min

        base_confidence = signal.confidence_score or 0
        adjusted = base_confidence * decay

        return max(adjusted, base_confidence * 0.3)  # Minimum 30% of original

    except Exception as e:
        async_to_sync(log_event)(f"Error calculando confidence ajustado: {e}",
                                 source='risk_manager', level='ERROR')
        return signal.confidence_score or 0


def is_signal_active(signal, current_time):
    """
    Determina si una señal aún está activa con lógica mejorada
    """
    try:
        duration = signal.strategy.validity_minutes if signal.strategy else 15

        # Extend duration for high-confidence signals
        confidence = signal.confidence_score or 50
        if confidence >= 80:
            duration *= 1.5  # 50% longer for high confidence
        elif confidence >= 70:
            duration *= 1.2  # 20% longer for good confidence
        elif confidence < 40:
            duration *= 0.8  # 20% shorter for low confidence

        start_time = getattr(signal, "timestamp", None) or getattr(signal, "received_at", None)
        if not start_time:
            return False

        expires_at = start_time + timedelta(minutes=duration)
        return current_time <= expires_at

    except Exception as e:
        async_to_sync(log_event)(f"Error verificando signal activa: {e}",
                                 source='risk_manager', level='ERROR')
        return False


def get_active_signals(symbol_name, execution_mode="simulated", current_time=None):
    """
    Devuelve señales activas con filtrado inteligente mejorado
    """
    from signals.signal import Signal as LiveSignal
    from backtesting.models.HistoricalSignal import Signal as HistoricalSignal

    current_time = current_time or timezone.now()

    try:
        if execution_mode == "backtest":
            if current_time is None:
                raise ValueError("❌ current_time debe pasarse en modo backtest")
            signals = HistoricalSignal.objects.filter(
                market_data__symbol=symbol_name
            ).select_related('strategy')
        else:
            signals = LiveSignal.objects.filter(
                symbol__symbol=symbol_name
            ).select_related('strategy', 'symbol')

        # Filter active signals
        active_signals = [s for s in signals if is_signal_active(s, current_time)]

        # Additional quality filtering
        quality_signals = []
        for signal in active_signals:
            # Skip signals without strategy
            if not signal.strategy:
                continue

            # Skip very low confidence signals
            confidence = signal.confidence_score or 0
            if confidence < 25:  # Below minimum threshold
                continue

            # Skip signals from inactive strategies
            if hasattr(signal.strategy, 'auto_execute') and not signal.strategy.auto_execute:
                continue

            quality_signals.append(signal)

        if len(quality_signals) != len(active_signals):
            async_to_sync(log_event)(
                f"📡 Signals filtered: {len(active_signals)} → {len(quality_signals)} for {symbol_name}",
                source='risk_manager', level='INFO'
            )

        return quality_signals

    except Exception as e:
        async_to_sync(log_event)(f"Error obteniendo señales activas: {e}",
                                 source='risk_manager', level='ERROR')
        return []


def calculate_signal_strength(signals):
    """
    Calcula la fuerza general de un conjunto de señales
    """
    if not signals:
        return 0

    try:
        total_weight = 0
        weighted_confidence = 0

        priority_weights = {"Primary": 1.0, "Context": 0.8, "Confirm": 0.6}

        for signal in signals:
            confidence = get_adjusted_confidence(signal)
            priority = signal.strategy.priority.title() if signal.strategy else "Confirm"
            weight = priority_weights.get(priority, 0.6)

            total_weight += weight
            weighted_confidence += confidence * weight

        if total_weight == 0:
            return 0

        return weighted_confidence / total_weight

    except Exception as e:
        async_to_sync(log_event)(f"Error calculando signal strength: {e}",
                                 source='risk_manager', level='ERROR')
        return 0


def validate_trade_timing(signal, current_time=None):
    """
    Valida si es buen momento para ejecutar un trade basado en la señal
    """
    current_time = current_time or now()

    try:
        # Check signal freshness
        signal_age = (current_time - signal.received_at).total_seconds() / 60

        # Prefer fresh signals
        if signal_age < 5:
            timing_score = 1.0
        elif signal_age < 15:
            timing_score = 0.8
        elif signal_age < 30:
            timing_score = 0.6
        else:
            timing_score = 0.4

        # Check market hours (basic implementation)
        hour = current_time.hour
        if 9 <= hour <= 16:  # Market hours
            timing_score *= 1.1
        elif hour < 6 or hour > 20:  # Off hours
            timing_score *= 0.8

        return timing_score >= 0.6, timing_score

    except Exception as e:
        async_to_sync(log_event)(f"Error validando timing: {e}",
                                 source='risk_manager', level='ERROR')
        return True, 0.5  # Default to allow trade
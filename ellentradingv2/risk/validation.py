from trades.models.trade import Trade
from monitoring.utils import log_event
from asgiref.sync import async_to_sync
from django.utils.timezone import now, timedelta
from django.db.models import Sum


def is_symbol_already_in_position(symbol):
    """
    Verifica si ya existe un trade abierto para este símbolo.
    """
    return Trade.objects.filter(symbol=symbol, status="EXECUTED").exists()


def is_crypto(symbol):
    """
    Detecta si el activo pertenece al mercado cripto usando asset_class.
    """
    return symbol.asset_class == "crypto"


def get_portfolio_exposure():
    """
    Calcula la exposición actual del portafolio
    """
    try:
        active_trades = Trade.objects.filter(status="EXECUTED")
        total_exposure = 0

        for trade in active_trades:
            if trade.notional:
                total_exposure += trade.notional
            elif trade.quantity and trade.symbol.live_price:
                total_exposure += trade.quantity * trade.symbol.live_price

        return total_exposure
    except Exception as e:
        async_to_sync(log_event)(f"Error calculando exposición: {e}", source='risk_manager', level='ERROR')
        return 0


def get_symbol_correlation_risk(symbol):
    """
    Evalúa riesgo de correlación con posiciones existentes
    """
    try:
        active_trades = Trade.objects.filter(status="EXECUTED").select_related('symbol')

        # Cryptocurrencies correlation
        if is_crypto(symbol):
            crypto_trades = [t for t in active_trades if is_crypto(t.symbol)]
            if len(crypto_trades) >= 3:  # Ya hay muchas cryptos
                return 0.7  # Reduce size by 30%
            elif len(crypto_trades) >= 2:
                return 0.85  # Reduce size by 15%

        # Same sector correlation (básico)
        same_asset_class = [t for t in active_trades if t.symbol.asset_class == symbol.asset_class]
        if len(same_asset_class) >= 5:
            return 0.8  # Reduce size by 20%
        elif len(same_asset_class) >= 3:
            return 0.9  # Reduce size by 10%

        return 1.0  # No correlation risk
    except Exception:
        return 1.0


def calculate_volatility_multiplier(symbol):
    """
    Calcula multiplicador basado en volatilidad del símbolo
    """
    try:
        # Get recent trades for this symbol to estimate volatility
        recent_trades = Trade.objects.filter(
            symbol=symbol,
            status__in=["EXECUTED", "CLOSED"],
            executed_at__gte=now() - timedelta(days=30)
        )

        if recent_trades.count() < 3:
            return 1.0  # Default if not enough data

        # Calculate PnL volatility
        pnls = [t.pnl for t in recent_trades if t.pnl is not None]
        if len(pnls) < 2:
            return 1.0

        avg_pnl = sum(pnls) / len(pnls)
        variance = sum((pnl - avg_pnl) ** 2 for pnl in pnls) / len(pnls)
        volatility = variance ** 0.5

        # High volatility = smaller position
        if volatility > 100:  # High volatility
            return 0.7
        elif volatility > 50:  # Medium volatility
            return 0.85
        else:  # Low volatility
            return 1.1  # Can take slightly larger position

    except Exception:
        return 1.0


def calculate_confidence_multiplier(confidence_score):
    """
    Calcula multiplicador basado en confidence score de la señal
    """
    # Rangos universales: 30-100
    if confidence_score >= 80:
        return 1.3  # High confidence = larger position
    elif confidence_score >= 70:
        return 1.15
    elif confidence_score >= 60:
        return 1.0
    elif confidence_score >= 50:
        return 0.9
    elif confidence_score >= 40:
        return 0.8
    else:
        return 0.7  # Low confidence = smaller position


def calculate_dynamic_position_size(price, symbol, capital, base_risk_pct, confidence_score):
    """
    Calcula tamaño de posición dinámico basado en múltiples factores
    """
    # Multiplicadores de riesgo
    confidence_mult = calculate_confidence_multiplier(confidence_score)
    volatility_mult = calculate_volatility_multiplier(symbol)
    correlation_mult = get_symbol_correlation_risk(symbol)

    # Risk management por exposición del portafolio
    current_exposure = get_portfolio_exposure()
    exposure_ratio = current_exposure / capital if capital > 0 else 0

    if exposure_ratio > 0.8:  # Portfolio muy expuesto
        exposure_mult = 0.5
    elif exposure_ratio > 0.6:
        exposure_mult = 0.7
    elif exposure_ratio > 0.4:
        exposure_mult = 0.85
    else:
        exposure_mult = 1.0

    # Calcular risk percentage ajustado
    adjusted_risk_pct = base_risk_pct * confidence_mult * volatility_mult * correlation_mult * exposure_mult

    # Cap the risk
    adjusted_risk_pct = min(adjusted_risk_pct, base_risk_pct * 1.5)  # Max 1.5x base risk
    adjusted_risk_pct = max(adjusted_risk_pct, base_risk_pct * 0.3)  # Min 0.3x base risk

    max_allocation = capital * adjusted_risk_pct

    async_to_sync(log_event)(
        f"💡 Dynamic sizing: base_risk={base_risk_pct:.1%} → adjusted={adjusted_risk_pct:.1%} "
        f"(conf={confidence_mult:.2f}, vol={volatility_mult:.2f}, corr={correlation_mult:.2f}, exp={exposure_mult:.2f})",
        source='risk_manager', level='INFO'
    )

    if is_crypto(symbol):
        # Crypto: siempre usar notional
        notional = min(max_allocation, capital * 0.3)  # Cap crypto at 30% of capital
        return {"mode": "notional", "value": round(notional, 2)}

    # Stocks: usar qty si alcanza, sino usar notional
    qty = int(max_allocation // price)
    if qty >= 1:
        return {"mode": "qty", "value": qty}
    else:
        return {"mode": "notional", "value": round(max_allocation, 2)}


def check_daily_trade_limits(symbol):
    """
    Verifica límites de trading diario
    """
    today = now().date()

    # Límite de trades por símbolo por día
    symbol_trades_today = Trade.objects.filter(
        symbol=symbol,
        executed_at__date=today
    ).count()

    if symbol_trades_today >= 3:  # Max 3 trades per symbol per day
        return False, "Daily symbol trade limit reached (3)"

    # Límite total de trades por día
    total_trades_today = Trade.objects.filter(
        executed_at__date=today
    ).count()

    if total_trades_today >= 10:  # Max 10 trades per day
        return False, "Daily total trade limit reached (10)"

    return True, "Within daily limits"


def check_portfolio_risk_limits(capital, new_trade_size):
    """
    Verifica límites de riesgo a nivel de portafolio
    """
    current_exposure = get_portfolio_exposure()
    total_exposure_after = current_exposure + new_trade_size

    # No más del 95% del capital en trades activos
    if total_exposure_after > capital * 0.95:
        return False, f"Portfolio exposure limit: {total_exposure_after:.0f} > {capital * 0.95:.0f}"

    # Check for concentration risk
    active_trades_count = Trade.objects.filter(status="EXECUTED").count()
    if active_trades_count >= 8:  # Max 8 concurrent positions
        return False, "Maximum concurrent positions reached (8)"

    return True, "Portfolio risk within limits"


def can_execute_trade(signal, price, capital, risk_pct, min_notional):
    """
    Evaluación completa de si se puede ejecutar el trade con risk management avanzado
    """
    symbol = signal.symbol
    confidence_score = signal.confidence_score or 50

    # Check 1: Posición existente
    if is_symbol_already_in_position(symbol):
        async_to_sync(log_event)(f"🚫 Trade bloqueado: posición activa para {symbol}", source='risk_manager',
                                 level='INFO')
        return False, "Trade already active for this symbol"

    # Check 2: Límites diarios
    daily_ok, daily_reason = check_daily_trade_limits(symbol)
    if not daily_ok:
        async_to_sync(log_event)(f"🚫 Trade bloqueado: {daily_reason}", source='risk_manager', level='INFO')
        return False, daily_reason

    # Check 3: Calcular tamaño dinámico
    size = calculate_dynamic_position_size(price, symbol, capital, risk_pct, confidence_score)

    # Check 4: Validar tamaño mínimo
    if size["mode"] == "qty":
        amount_usd = size["value"] * price
        if size["value"] <= 0:
            async_to_sync(log_event)("🚫 Trade bloqueado: capital insuficiente para qty mínima", source='risk_manager',
                                     level='INFO')
            return False, "Insufficient capital for minimum qty"
    else:
        amount_usd = size["value"]
        if amount_usd < min_notional:
            async_to_sync(log_event)("🚫 Trade bloqueado: notional muy pequeño", source='risk_manager', level='INFO')
            return False, f"Minimum notional too small (below ${min_notional})"

    # Check 5: Límites de portafolio
    portfolio_ok, portfolio_reason = check_portfolio_risk_limits(capital, amount_usd)
    if not portfolio_ok:
        async_to_sync(log_event)(f"🚫 Trade bloqueado: {portfolio_reason}", source='risk_manager', level='INFO')
        return False, portfolio_reason

    # Check 6: Sanity check - no más del 20% del capital en un solo trade
    if amount_usd > capital * 0.2:
        adjusted_amount = capital * 0.2
        if size["mode"] == "qty":
            size["value"] = int(adjusted_amount // price)
            amount_usd = size["value"] * price
        else:
            size["value"] = adjusted_amount
            amount_usd = adjusted_amount

        async_to_sync(log_event)(
            f"⚠️ Trade size reducido por límite de concentración: ${amount_usd:.0f}",
            source='risk_manager', level='INFO'
        )

    async_to_sync(log_event)(
        f"✅ Trade aprobado: ${amount_usd:.0f} ({amount_usd / capital:.1%} del capital)",
        source='risk_manager', level='INFO'
    )

    return True, amount_usd
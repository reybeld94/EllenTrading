from risk.risk_settings import RiskSettings
from risk.config_defaults import RiskConfigDefaults
from risk.utils import get_active_signals
from django.utils.timezone import now, timedelta
from alpaca.trading.client import TradingClient
from trades.models.portfolio import Portfolio
from trades.models.trade import Trade
from monitoring.utils import log_event
from asgiref.sync import async_to_sync
from django.db.models import Avg, Count

ALPACA_API_KEY = "PKALPV6774BZYC8TQ29Q"
ALPACA_SECRET_KEY = "tUczQ1yDfIQMQzXubtwmpBFiJj8JNZhkMc8gYQaT"


def analyze_market_conditions():
    """
    Analiza condiciones de mercado para ajustes dinámicos
    """
    try:
        # Analizar trades recientes para detectar condiciones
        recent_trades = Trade.objects.filter(
            executed_at__gte=now() - timedelta(hours=24),
            status__in=["EXECUTED", "CLOSED"]
        )

        if recent_trades.count() < 5:
            return {
                "volatility": "normal",
                "trend_strength": "neutral",
                "success_rate": 0.5,
                "avg_duration": 60,
                "recommendation": "normal"
            }

        # Calcular métricas de mercado
        closed_trades = recent_trades.filter(status="CLOSED", pnl__isnull=False)

        if closed_trades.count() > 0:
            success_rate = closed_trades.filter(pnl__gt=0).count() / closed_trades.count()
            avg_pnl = closed_trades.aggregate(avg_pnl=Avg('pnl'))['avg_pnl'] or 0

            # Calcular volatilidad basada en PnL
            pnls = [t.pnl for t in closed_trades if t.pnl is not None]
            if len(pnls) >= 3:
                avg_pnl_calc = sum(pnls) / len(pnls)
                variance = sum((pnl - avg_pnl_calc) ** 2 for pnl in pnls) / len(pnls)
                volatility_measure = (variance ** 0.5) / abs(avg_pnl_calc) if avg_pnl_calc != 0 else 1
            else:
                volatility_measure = 1
        else:
            success_rate = 0.5
            avg_pnl = 0
            volatility_measure = 1

        # Analizar duración promedio de trades
        duration_data = []
        for trade in closed_trades:
            if trade.executed_at and trade.closed_at:
                duration = (trade.closed_at - trade.executed_at).total_seconds() / 60
                duration_data.append(duration)

        avg_duration = sum(duration_data) / len(duration_data) if duration_data else 60

        # Clasificar condiciones
        if volatility_measure > 2:
            volatility = "high"
        elif volatility_measure > 1.5:
            volatility = "medium"
        else:
            volatility = "low"

        if success_rate > 0.7:
            trend_strength = "strong"
        elif success_rate > 0.5:
            trend_strength = "medium"
        else:
            trend_strength = "weak"

        # Recomendación general
        if volatility == "high" and success_rate < 0.4:
            recommendation = "conservative"
        elif volatility == "low" and success_rate > 0.6:
            recommendation = "aggressive"
        else:
            recommendation = "normal"

        return {
            "volatility": volatility,
            "trend_strength": trend_strength,
            "success_rate": success_rate,
            "avg_duration": avg_duration,
            "recommendation": recommendation,
            "avg_pnl": avg_pnl
        }

    except Exception as e:
        async_to_sync(log_event)(f"Error analizando condiciones de mercado: {e}", source='risk_manager', level='ERROR')
        return {
            "volatility": "normal",
            "trend_strength": "neutral",
            "success_rate": 0.5,
            "avg_duration": 60,
            "recommendation": "normal"
        }


def get_dynamic_config_adjustments(market_conditions):
    """
    Genera ajustes dinámicos de configuración basados en condiciones de mercado
    """
    adjustments = {}

    # Ajustes por volatilidad
    if market_conditions["volatility"] == "high":
        adjustments.update({
            "risk_pct": 0.08,  # Reduce risk in high volatility
            "conflict_threshold": 20,  # Be more selective
            "primary_min_score": 50,
            "context_confirm_avg_score": 47,
            "sl_buffer_pct": 0.025,  # Wider stops
            "tp_buffer_pct": 0.06  # Wider targets
        })
    elif market_conditions["volatility"] == "low":
        adjustments.update({
            "risk_pct": 0.12,  # Increase risk in low volatility
            "conflict_threshold": 12,  # Be more aggressive
            "primary_min_score": 42,
            "context_confirm_avg_score": 40,
            "sl_buffer_pct": 0.018,  # Tighter stops
            "tp_buffer_pct": 0.045  # Tighter targets
        })

    # Ajustes por trend strength
    if market_conditions["trend_strength"] == "strong":
        adjustments.update({
            "strategy_weights": {
                "Primary": 1.3,  # More weight to trend-following
                "Context": 1.0,
                "Confirm": 0.8
            }
        })
    elif market_conditions["trend_strength"] == "weak":
        adjustments.update({
            "strategy_weights": {
                "Primary": 1.0,
                "Context": 1.2,  # More weight to context
                "Confirm": 1.1  # More confirmation needed
            }
        })

    # Ajustes por success rate
    if market_conditions["success_rate"] < 0.4:
        adjustments.update({
            "primary_min_score": 55,  # Higher thresholds
            "context_confirm_avg_score": 50,
            "confirm_min_avg_score": 45
        })
    elif market_conditions["success_rate"] > 0.7:
        adjustments.update({
            "primary_min_score": 40,  # Lower thresholds
            "context_confirm_avg_score": 38,
            "confirm_min_avg_score": 35
        })

    # Ajustes por duración promedio
    if market_conditions["avg_duration"] < 30:  # Very fast trades
        adjustments.update({
            "trailing_stop_pct": 0.015,  # Tighter trailing
            "tp_buffer_pct": 0.04  # Quicker profits
        })
    elif market_conditions["avg_duration"] > 180:  # Slow trades
        adjustments.update({
            "trailing_stop_pct": 0.008,  # Looser trailing
            "tp_buffer_pct": 0.07  # Bigger targets
        })

    return adjustments


def get_enhanced_default_config():
    """
    Configuración por defecto mejorada para rangos universales
    """
    return {
        # Risk Management
        "risk_pct": 0.10,  # 10% per trade (era 0.02)
        "min_notional": 50,  # $50 minimum

        # Decision Making - Optimized for universal ranges
        "conflict_threshold": 15,  # Era 10
        "strategy_weights": {
            "Primary": 1.2,  # Era 1.0 (más peso)
            "Context": 0.9,  # Era 0.7 (más peso)
            "Confirm": 0.7  # Era 0.5 (más peso)
        },

        # Scoring Thresholds - Optimized for 30-100 ranges
        "primary_min_score": 45,  # Era 50
        "context_confirm_avg_score": 42,  # Era 50
        "confirm_min_avg_score": 40,  # Era 50
        "primary_group_avg_score": 48,  # Era 50

        # Exit Parameters
        "sl_buffer_pct": 0.02,  # 2% stop loss
        "tp_buffer_pct": 0.05,  # 5% take profit
        "trailing_stop_pct": 0.01,  # 1% trailing stop

        # Portfolio Management
        "max_positions": 8,  # Maximum concurrent positions
        "max_symbol_exposure": 0.2,  # 20% max per symbol
        "max_sector_exposure": 0.4,  # 40% max per sector

        # Dynamic Features
        "enable_dynamic_sizing": True,
        "enable_market_regime_detection": True,
        "enable_correlation_analysis": True
    }


def load_risk_context(symbol_name, execution_mode="simulated", capital_override=None, config_override=None):
    """
    Carga contexto de riesgo con configuraciones dinámicas mejoradas
    """
    # ✅ 1. Config base mejorada
    base_config = get_enhanced_default_config()

    if config_override is not None:
        # Merge config override with base config
        merged_config = base_config.copy()
        merged_config.update(config_override)
        config = merged_config
    else:
        try:
            db_config = RiskSettings.objects.get(name="default").as_config_dict()
            # Merge DB config with enhanced base config
            merged_config = base_config.copy()
            merged_config.update(db_config)
            config = merged_config
        except RiskSettings.DoesNotExist:
            async_to_sync(log_event)("❌ No se encontró configuración en base de datos. Usando config mejorada.",
                                     source='risk_manager', level='WARNING')
            config = base_config

    # ✅ 2. Análisis de condiciones de mercado y ajustes dinámicos
    market_conditions = analyze_market_conditions()
    dynamic_adjustments = get_dynamic_config_adjustments(market_conditions)

    # Aplicar ajustes dinámicos
    config.update(dynamic_adjustments)

    async_to_sync(log_event)(
        f"📊 Market conditions: {market_conditions['recommendation']} "
        f"(volatility: {market_conditions['volatility']}, "
        f"success: {market_conditions['success_rate']:.1%}, "
        f"trend: {market_conditions['trend_strength']})",
        source='risk_manager', level='INFO'
    )

    # ✅ 3. Capital management
    if execution_mode in ("paper", "live"):
        alpaca = TradingClient(ALPACA_API_KEY, ALPACA_SECRET_KEY, paper=(execution_mode == "paper"))
        capital = get_available_capital(alpaca)
    elif execution_mode == "simulated":
        try:
            portfolio = Portfolio.objects.get(name="Simulado")
            capital = portfolio.usd_balance

            # Dynamic capital adjustment based on recent performance
            if market_conditions["success_rate"] < 0.3:
                # Reduce effective capital in bad conditions
                capital = capital * 0.7
                async_to_sync(log_event)("⚠️ Capital reducido por poor performance", source='risk_manager',
                                         level='INFO')
            elif market_conditions["success_rate"] > 0.8:
                # Can use more capital in good conditions (but cap it)
                capital = min(capital * 1.1, portfolio.usd_balance)

        except Portfolio.DoesNotExist:
            async_to_sync(log_event)(f"❌ Portafolio 'Simulado' no existe",
                                     source='risk_manager', level='ERROR')
            capital = 0
        alpaca = None
    else:
        alpaca = None
        capital = capital_override if capital_override is not None else 10_000

    # ✅ 4. Señales con filtrado inteligente
    if execution_mode != "backtest":
        all_signals = get_active_signals(symbol_name, execution_mode=execution_mode, current_time=now())

        # Filter signals based on market conditions
        filtered_signals = []
        for signal in all_signals:
            # Skip low confidence signals in bad market conditions
            if (market_conditions["recommendation"] == "conservative" and
                    signal.confidence_score < 55):
                continue

            # Accept more signals in good conditions
            if (market_conditions["recommendation"] == "aggressive" or
                    signal.confidence_score >= 35):
                filtered_signals.append(signal)

        signals = filtered_signals

        async_to_sync(log_event)(
            f"📡 Signals: {len(all_signals)} → {len(signals)} (filtered by market conditions)",
            source='risk_manager', level='INFO'
        )
    else:
        signals = []

    # ✅ 5. Log final configuration
    async_to_sync(log_event)(
        f"⚙️ Config loaded: risk={config['risk_pct']:.1%}, "
        f"threshold={config['conflict_threshold']}, "
        f"capital=${capital:.0f}",
        source='risk_manager', level='INFO'
    )

    return config, capital, signals, alpaca


def get_available_capital(alpaca_client):
    """
    Obtiene capital disponible con validaciones mejoradas
    """
    try:
        account = alpaca_client.get_account()
        cash = float(account.cash)
        buying_power = float(account.buying_power)

        # Use the more conservative value
        available_capital = min(cash, buying_power)

        async_to_sync(log_event)(
            f"💰 Alpaca capital: cash=${cash:.0f}, buying_power=${buying_power:.0f}, using=${available_capital:.0f}",
            source='risk_manager', level='INFO'
        )

        return available_capital
    except Exception as e:
        async_to_sync(log_event)(f"❌ Error al obtener capital de Alpaca: {e}", source='risk_manager', level='ERROR')
        return 0
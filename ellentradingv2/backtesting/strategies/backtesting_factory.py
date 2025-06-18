from backtesting.strategies.macd_strategy import MACDBacktestStrategy
from backtesting.strategies.rsi_strategy import RSIBreakoutBacktestStrategy
from backtesting.strategies.ichimoku_strategy import IchimokuBacktestStrategy
from backtesting.strategies.adx_strategy import ADXBacktestStrategy
from backtesting.strategies.bollinger_strategy import BollingerBacktestStrategy
from backtesting.strategies.donchian_strategy import DonchianBacktestStrategy
from backtesting.strategies.volume_spike import VolumeSpikeBacktestStrategy
from backtesting.strategies.bullish_engulfing import BullishEngulfingBacktestStrategy
from backtesting.strategies.bearish_engulfing import BearishEngulfingBacktestStrategy
from backtesting.strategies.moving_average import MovingAverageCrossBacktestStrategy
from backtesting.strategies.stochastic_strategy import StochasticBacktestStrategy
from backtesting.strategies.parabolic_sar import ParabolicSARBacktestStrategy
from backtesting.strategies.cci_strategy import CCIBacktestStrategy


def build_backtest_strategy(strategy_instance):
    name = strategy_instance.name.lower()

    if "macd" in name:
        return MACDBacktestStrategy(strategy_instance)

    elif "rsi" in name:
        return RSIBreakoutBacktestStrategy(strategy_instance)

    elif "ichimoku" in name:
        return IchimokuBacktestStrategy(strategy_instance)

    elif "adx" in name:
        return ADXBacktestStrategy(strategy_instance)

    elif "bollinger" in name:
        return BollingerBacktestStrategy(strategy_instance)

    elif "donchian" in name:
        return DonchianBacktestStrategy(strategy_instance)

    elif "volume" in name:
        return VolumeSpikeBacktestStrategy(strategy_instance)

    elif "bullish" in name:
        return BullishEngulfingBacktestStrategy(strategy_instance)

    elif "bearish" in name:
        return BearishEngulfingBacktestStrategy(strategy_instance)

    elif "moving" in name:
        return MovingAverageCrossBacktestStrategy(strategy_instance)

    elif "stochastic" in name:
        return StochasticBacktestStrategy(strategy_instance)

    elif "parabolic" in name:
        return ParabolicSARBacktestStrategy(strategy_instance)

    elif "cci" in name:
        return CCIBacktestStrategy(strategy_instance)

    else:
        raise ValueError(f"❌ Estrategia no reconocida para backtest: {strategy_instance.name}")

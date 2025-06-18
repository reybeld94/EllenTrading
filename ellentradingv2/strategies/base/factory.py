from strategies.models import OpenStrategy

from strategies.strategies.moving_average import MovingAverageCrossStrategy
from strategies.strategies.rsi_strategy import RSIBreakoutStrategy
from strategies.strategies.bollinger_strategy import BollingerBandBreakoutStrategy
from strategies.strategies.macd_strategy import MACDCrossoverStrategy
from strategies.strategies.bullish_engulfing import BullishEngulfingStrategy
from strategies.strategies.bearish_engulfing import BearishEngulfingStrategy
from strategies.strategies.volume_spike import VolumeSpikeStrategy
from strategies.strategies.adx_strategy import ADXTrendStrengthStrategy
from strategies.strategies.ichimoku_strategy import IchimokuCloudBreakout
from strategies.strategies.parabolic_sar import ParabolicSARStrategy
from strategies.strategies.stochastic_strategy import StochasticOscillatorStrategy
from strategies.strategies.cci_strategy import CCIExtremeStrategy
from strategies.strategies.TripleEMACrossoverStrategy import TripleEMACrossoverStrategy
from strategies.strategies.DonchianChannelBreakoutStrategy import DonchianChannelBreakoutStrategy
from strategies.strategies.FibonacciRetracementStrategy import FibonacciRetracementStrategy


def build_entry_strategies():
    strategy_map = {}
    for s in OpenStrategy.objects.filter(auto_execute=True):
        name_map = {
            # ✨ NOMBRES EXACTOS que deben coincidir con la base de datos
            "Moving Average Cross Strategy": MovingAverageCrossStrategy,
            "RSI Breakout Strategy": RSIBreakoutStrategy,
            "Bollinger Band Breakout": BollingerBandBreakoutStrategy,
            "MACD Crossover Strategy": MACDCrossoverStrategy,
            "Bullish Engulfing Pattern": BullishEngulfingStrategy,
            "Bearish Engulfing Pattern": BearishEngulfingStrategy,
            "Volume Spike Breakout Strategy": VolumeSpikeStrategy,
            "ADX Trend Strength Strategy": ADXTrendStrengthStrategy,
            "Ichimoku Cloud Breakout": IchimokuCloudBreakout,
            "Parabolic SAR Trend Strategy": ParabolicSARStrategy,
            "Stochastic Oscillator Strategy": StochasticOscillatorStrategy,
            "CCI Extreme Strategy": CCIExtremeStrategy,
            "Triple EMA Crossover Strategy": TripleEMACrossoverStrategy,
            "Donchian Channel Breakout": DonchianChannelBreakoutStrategy,
            "Fibonacci Retracement Strategy": FibonacciRetracementStrategy,

            # ✨ ALIAS para backward compatibility (nombres alternativos)
            "Moving Average Crossover": MovingAverageCrossStrategy,
            "Volume Spike": VolumeSpikeStrategy,
            "Stochastic Oscillator": StochasticOscillatorStrategy,
        }

        class_ref = name_map.get(s.name)
        if class_ref:
            # Create a safe key for the strategy map
            key = s.name.lower().replace(" strategy", "").replace(" ", "_").replace("breakout", "").strip("_")
            strategy_map[key] = class_ref(strategy_instance=s)
        else:
            # ⚠️ Log strategies that couldn't be mapped
            print(f"⚠️ Strategy '{s.name}' not found in name_map. Available strategies:")
            for available_name in name_map.keys():
                print(f"   - {available_name}")

    return strategy_map


_entry_strategies_cache = None


def get_entry_strategy(name: str):
    global _entry_strategies_cache
    if _entry_strategies_cache is None:
        _entry_strategies_cache = build_entry_strategies()
    return _entry_strategies_cache.get(name)


def clear_strategy_cache():
    """Clear the strategy cache - useful for testing or reloading"""
    global _entry_strategies_cache
    _entry_strategies_cache = None


def list_available_strategies():
    """Debug function to see what strategies are available"""
    strategies = build_entry_strategies()
    print("🚀 Available strategies:")
    for key, strategy in strategies.items():
        print(f"   {key}: {strategy.name}")
    return strategies
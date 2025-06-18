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

def get_strategy_instance(strategy_model):
    name_map = {
        "Moving Average Crossover": MovingAverageCrossStrategy,
        "RSI Breakout Strategy": RSIBreakoutStrategy,
        "Bollinger Band Breakout": BollingerBandBreakoutStrategy,
        "MACD Crossover Strategy": MACDCrossoverStrategy,
        "Bullish Engulfing Pattern": BullishEngulfingStrategy,
        "Bearish Engulfing Pattern": BearishEngulfingStrategy,
        "Volume Spike": VolumeSpikeStrategy,
        "ADX Trend Strength Strategy": ADXTrendStrengthStrategy,
        "Ichimoku Cloud Breakout": IchimokuCloudBreakout,
        "Parabolic SAR Reversal": ParabolicSARStrategy,
        "Stochastic Oscillator": StochasticOscillatorStrategy,
        "CCI Extreme Strategy": CCIExtremeStrategy,
        "Triple EMA Crossover Strategy": TripleEMACrossoverStrategy,
        "Donchian Channel Breakout": DonchianChannelBreakoutStrategy,
        "Fibonacci Retracement Strategy": FibonacciRetracementStrategy,
    }

    class_ref = name_map.get(strategy_model.name)
    if class_ref:
        return class_ref(strategy_instance=strategy_model)
    return None

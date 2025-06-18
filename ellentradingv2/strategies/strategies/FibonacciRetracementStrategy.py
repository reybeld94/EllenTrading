from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from monitoring.utils import log_event
from asgiref.sync import async_to_sync


class FibonacciRetracementStrategy(EntryStrategy):
    name = "Fibonacci Retracement Strategy"

    def __init__(self, strategy_instance=None):
        self.name = "Fibonacci Retracement Strategy"
        self.required_bars = 100  # More bars for better swing detection
        super().__init__(strategy_instance)

    def fibonacci_levels(self, swing_high, swing_low):
        """Calcula todos los niveles Fibonacci importantes"""
        diff = swing_high - swing_low
        return {
            "0.0%": swing_high,
            "23.6%": swing_high - diff * 0.236,
            "38.2%": swing_high - diff * 0.382,
            "50.0%": swing_high - diff * 0.5,
            "61.8%": swing_high - diff * 0.618,
            "78.6%": swing_high - diff * 0.786,
            "100.0%": swing_low,
            # Extension levels
            "127.2%": swing_high - diff * 1.272,
            "161.8%": swing_high - diff * 1.618,
        }

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.required_bars:
            return None

        current_bar = bars[-1]
        current_price = current_bar.close

        # ✨ CONFIDENCE CON RANGOS UNIVERSALES ESTANDARIZADOS
        # Context strategy: base 35 (puede llegar a 60-80 con bonus)
        confidence = 35  # ⬇️ Ajustado de 70 a 35 para seguir rangos universales (Context priority)
        signal_type = None

        # ✨ MANTENER TODA LA LÓGICA COMPLETA: Detección de swings mejorada

        # Try different swing periods to find the best setup
        swing_periods = [20, 30, 50, 80]  # Different lookback periods
        best_signal = None
        best_confidence = 0

        for period in swing_periods:
            if len(bars) < period + 10:
                continue

            signal, conf_bonus = self._analyze_fibonacci_level(bars, current_price, period)
            if signal and conf_bonus > best_confidence:
                best_signal = signal
                best_confidence = conf_bonus

        if not best_signal:
            return None

        signal_type = best_signal
        confidence += best_confidence

        # ✨ MANTENER TODO EL SISTEMA DE BONUS COMPLETO

        # Bonus 1: Multiple Fibonacci confluence
        confluence_bonus = self._calculate_fibonacci_confluence(bars, current_price)
        confidence += confluence_bonus

        # Bonus 2: Fibonacci with trend alignment
        trend_bonus = self._calculate_trend_alignment_bonus(bars, signal_type)
        confidence += trend_bonus

        # Bonus 3: Volume at Fibonacci level
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 4: Price action at Fibonacci level
        price_action_bonus = self._calculate_price_action_bonus(current_bar, signal_type)
        confidence += price_action_bonus

        # Bonus 5: Fibonacci extension targets
        extension_bonus = self._calculate_extension_bonus(bars, current_price)
        confidence += extension_bonus

        # Bonus 6: Previous Fibonacci respect
        respect_bonus = self._calculate_fibonacci_respect_bonus(bars, current_price)
        confidence += respect_bonus

        # Bonus 7: Multi-timeframe Fibonacci alignment
        mtf_bonus = self._calculate_multi_timeframe_bonus(bars, current_price, signal_type)
        confidence += mtf_bonus

        # Bonus 8: Fibonacci cluster analysis
        cluster_bonus = self._calculate_fibonacci_cluster_bonus(bars, current_price)
        confidence += cluster_bonus

        # ✅ APLICAR RANGOS UNIVERSALES
        confidence = min(int(confidence), 100)

        # ✅ THRESHOLD AJUSTADO A RANGOS UNIVERSALES
        # Para Context: 55 (DECENTE alto) mínimo, 70+ (BUENA/FUERTE) preferido
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 55)
        if confidence < min_confidence:
            return None

        # ✅ OPCIONAL: Log del rango alcanzado
        quality_level = self._get_quality_description(confidence)
        async_to_sync(log_event)(f"📊 Fibonacci Score: {confidence} - {quality_level}",
                                 source='strategies', level='INFO')

        # Evitar duplicados
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="fibonacci_retracement",
            strategy=self.strategy_instance,
            received_at__gte=recent_cutoff
        ).exists()

        if recent_signal:
            return None

        # Crear señal
        s = Signal(
            symbol=symbol_obj,
            signal=signal_type,
            price=current_price,
            confidence_score=confidence,
            source="fibonacci_retracement",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(bars[-1], "timestamp", getattr(bars[-1], "start_time", None))
        s.received_at = s.timestamp

        async_to_sync(log_event)(
            f"🌟 FIBONACCI GOLDEN: {signal_type} for {symbol_obj.symbol} | Price: {current_price:.4f} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s

    def _get_quality_description(self, score: int) -> str:
        """Determina el nivel de calidad según rangos universales"""
        if score <= 34:
            return "🔴 RUIDO"
        elif score <= 49:
            return "🟡 DÉBIL"
        elif score <= 64:
            return "🟠 DECENTE"
        elif score <= 74:
            return "🟢 BUENA"
        elif score <= 84:
            return "🔵 FUERTE"
        else:
            return "🟣 EXCELENTE"

    def _analyze_fibonacci_level(self, bars, current_price, period):
        """Analiza si el precio está en un nivel Fibonacci significativo"""

        # ✨ DETECCIÓN DE SWINGS MEJORADA
        swing_high, swing_low = self._find_significant_swing(bars, period)

        if swing_high <= swing_low:
            return None, 0

        levels = self.fibonacci_levels(swing_high, swing_low)

        # ✨ ANÁLISIS DE MÚLTIPLES NIVELES FIBONACCI
        for level_name, level_price in levels.items():
            if level_name in ["0.0%", "100.0%"]:  # Skip extremes
                continue

            # ✨ MARGEN MÁS GENEROSO (era 0.5%, ahora escala con volatilidad)
            price_range = swing_high - swing_low
            margin = max(price_range * 0.01, current_price * 0.005)  # 1% of range or 0.5% of price

            if abs(current_price - level_price) <= margin:
                return self._determine_fibonacci_signal(
                    current_price, level_price, level_name, swing_high, swing_low, bars
                )

        return None, 0

    def _find_significant_swing(self, bars, period):
        """Encuentra swings significativos usando pivots"""

        if len(bars) < period + 10:
            # Fallback to simple high/low
            highs = [bar.high for bar in bars[-period:]]
            lows = [bar.low for bar in bars[-period:]]
            return max(highs), min(lows)

        # ✨ DETECCIÓN DE PIVOTS MEJORADA
        swing_high = 0
        swing_low = float('inf')

        # Look for pivot highs and lows
        for i in range(5, len(bars) - 5):  # Need 5 bars on each side
            current_high = bars[i].high
            current_low = bars[i].low

            # Check if it's a pivot high
            is_pivot_high = all(current_high >= bars[j].high for j in range(i - 5, i + 6) if j != i)
            if is_pivot_high and current_high > swing_high:
                swing_high = current_high

            # Check if it's a pivot low
            is_pivot_low = all(current_low <= bars[j].low for j in range(i - 5, i + 6) if j != i)
            if is_pivot_low and current_low < swing_low:
                swing_low = current_low

        # Fallback if no significant pivots found
        if swing_high == 0 or swing_low == float('inf'):
            highs = [bar.high for bar in bars[-period:]]
            lows = [bar.low for bar in bars[-period:]]
            swing_high = max(highs)
            swing_low = min(lows)

        return swing_high, swing_low

    def _determine_fibonacci_signal(self, current_price, level_price, level_name, swing_high, swing_low, bars):
        """Determina el tipo de señal basado en el nivel Fibonacci"""

        # ✨ LÓGICA FIBONACCI MEJORADA
        base_bonus = 15

        # Determine if we're in an uptrend or downtrend
        recent_trend = (bars[-1].close - bars[-20].close) / bars[-20].close if len(bars) >= 20 else 0

        # ✨ SEÑALES POR NIVEL FIBONACCI
        if level_name == "23.6%":
            # Shallow retracement - strong trend continuation
            if recent_trend > 0.02:  # Uptrend
                return SignalType.BUY, base_bonus + 5
            elif recent_trend < -0.02:  # Downtrend
                return SignalType.SELL, base_bonus + 5

        elif level_name == "38.2%":
            # Moderate retracement - good entry for trend continuation
            if recent_trend > 0.01:
                return SignalType.BUY, base_bonus + 8
            elif recent_trend < -0.01:
                return SignalType.SELL, base_bonus + 8

        elif level_name == "50.0%":
            # Half retracement - psychological level
            if recent_trend > 0.005:
                return SignalType.BUY, base_bonus + 6
            elif recent_trend < -0.005:
                return SignalType.SELL, base_bonus + 6

        elif level_name == "61.8%":
            # Golden ratio - most important Fibonacci level
            if recent_trend > 0:
                return SignalType.BUY, base_bonus + 12  # Highest bonus
            elif recent_trend < 0:
                return SignalType.SELL, base_bonus + 12

        elif level_name == "78.6%":
            # Deep retracement - potential reversal or strong continuation
            return SignalType.BUY, base_bonus + 10  # Often bullish at deep retracement

        # Extension levels
        elif level_name in ["127.2%", "161.8%"]:
            # Price beyond 100% - potential reversal zones
            if current_price > swing_high:  # Above swing high
                return SignalType.SELL, base_bonus + 8  # Potential resistance
            elif current_price < swing_low:  # Below swing low
                return SignalType.BUY, base_bonus + 8  # Potential support

        return None, 0

    def _calculate_fibonacci_confluence(self, bars, current_price):
        """Calcula bonus por confluencia de múltiples niveles Fibonacci"""
        confluence_count = 0

        # Check different swing periods for confluence
        periods = [20, 30, 50]
        for period in periods:
            if len(bars) < period + 10:
                continue

            swing_high, swing_low = self._find_significant_swing(bars, period)
            if swing_high <= swing_low:
                continue

            levels = self.fibonacci_levels(swing_high, swing_low)

            # Check if current price is near any Fibonacci level
            for level_price in levels.values():
                margin = current_price * 0.01  # 1% margin
                if abs(current_price - level_price) <= margin:
                    confluence_count += 1
                    break

        if confluence_count >= 3:
            return 15  # Strong confluence
        elif confluence_count >= 2:
            return 10  # Moderate confluence
        elif confluence_count >= 1:
            return 5  # Some confluence
        else:
            return 0

    def _calculate_trend_alignment_bonus(self, bars, signal_type):
        """Calcula bonus por alineación con tendencia"""
        if len(bars) < 20:
            return 0

        # Multiple timeframe trend analysis
        short_trend = (bars[-1].close - bars[-5].close) / bars[-5].close  # 5-bar trend
        medium_trend = (bars[-1].close - bars[-20].close) / bars[-20].close  # 20-bar trend

        bonus = 0
        if signal_type == SignalType.BUY:
            if short_trend > 0.01 and medium_trend > 0.02:
                bonus = 12  # Strong aligned uptrend
            elif short_trend > 0 and medium_trend > 0:
                bonus = 8  # Moderate aligned uptrend
        elif signal_type == SignalType.SELL:
            if short_trend < -0.01 and medium_trend < -0.02:
                bonus = 12  # Strong aligned downtrend
            elif short_trend < 0 and medium_trend < 0:
                bonus = 8  # Moderate aligned downtrend

        return bonus

    def _calculate_volume_bonus(self, bars, current_bar):
        """Calcula bonus basado en volumen en nivel Fibonacci"""
        try:
            current_volume = getattr(current_bar, 'volume', None) or self.get_indicator_value(current_bar, "volume")
            if not current_volume or len(bars) < 10:
                return 0

            volumes = []
            for bar in bars[-10:]:
                vol = getattr(bar, 'volume', None) or self.get_indicator_value(bar, "volume")
                if vol:
                    volumes.append(vol)

            if not volumes:
                return 0

            avg_volume = sum(volumes) / len(volumes)
            volume_ratio = current_volume / avg_volume

            if volume_ratio > 1.8:
                return 10  # High volume at Fibonacci level
            elif volume_ratio > 1.4:
                return 6
            elif volume_ratio > 1.1:
                return 3
            else:
                return 0
        except:
            return 0

    def _calculate_price_action_bonus(self, current_bar, signal_type):
        """Calcula bonus basado en price action en nivel Fibonacci"""
        candle_body = abs(current_bar.close - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        # Strong rejection candle at Fibonacci level
        if signal_type == SignalType.BUY:
            # Long lower wick (rejection of lower prices)
            lower_wick = current_bar.open - current_bar.low if current_bar.close > current_bar.open else current_bar.close - current_bar.low
            if lower_wick > candle_body * 2:  # Wick > 2x body
                return 12
            elif current_bar.close > current_bar.open and body_ratio > 0.6:
                return 8  # Strong green candle
        elif signal_type == SignalType.SELL:
            # Long upper wick (rejection of higher prices)
            upper_wick = current_bar.high - current_bar.open if current_bar.close < current_bar.open else current_bar.high - current_bar.close
            if upper_wick > candle_body * 2:  # Wick > 2x body
                return 12
            elif current_bar.close < current_bar.open and body_ratio > 0.6:
                return 8  # Strong red candle

        return 0

    def _calculate_extension_bonus(self, bars, current_price):
        """Calcula bonus si precio está en extension levels"""
        if len(bars) < 50:
            return 0

        # Look for extension beyond recent swings
        swing_high, swing_low = self._find_significant_swing(bars, 30)

        if swing_high <= swing_low:
            return 0

        # Check if price is at extension levels
        range_size = swing_high - swing_low

        # 127.2% extension
        ext_127 = swing_high + range_size * 0.272
        ext_162 = swing_high + range_size * 0.618

        margin = current_price * 0.01

        if abs(current_price - ext_127) <= margin or abs(current_price - ext_162) <= margin:
            return 8  # At extension level

        return 0

    def _calculate_fibonacci_respect_bonus(self, bars, current_price):
        """Calcula bonus si precio ha respetado niveles Fibonacci anteriormente"""
        if len(bars) < 50:
            return 0

        respect_count = 0

        # Check last 30 bars for Fibonacci respect
        for i in range(-30, -1):
            try:
                bar = bars[i]
                # Simplified: check if price bounced near round numbers (Fibonacci-like behavior)
                price_rounded = round(bar.low, 1)
                if abs(bar.close - price_rounded) / price_rounded < 0.005:  # 0.5% near round number
                    respect_count += 1
            except:
                continue

        if respect_count >= 5:
            return 8  # High Fibonacci respect
        elif respect_count >= 3:
            return 5  # Moderate respect
        else:
            return 0

    def _calculate_multi_timeframe_bonus(self, bars, current_price, signal_type):
        """Calcula bonus por alineación multi-timeframe simulada"""
        if len(bars) < 60:
            return 0

        # Simulate higher timeframe by sampling every 4th bar
        htf_bars = bars[::4]  # Every 4th bar

        if len(htf_bars) < 20:
            return 0

        # Check HTF Fibonacci levels
        htf_swing_high, htf_swing_low = self._find_significant_swing(htf_bars, 15)

        if htf_swing_high <= htf_swing_low:
            return 0

        htf_levels = self.fibonacci_levels(htf_swing_high, htf_swing_low)

        # Check if current price aligns with HTF Fibonacci
        for level_price in htf_levels.values():
            margin = current_price * 0.015  # 1.5% margin for HTF
            if abs(current_price - level_price) <= margin:
                return 10  # HTF Fibonacci alignment

        return 0

    def _calculate_fibonacci_cluster_bonus(self, bars, current_price):
        """Calcula bonus por cluster de niveles Fibonacci"""
        if len(bars) < 40:
            return 0

        cluster_levels = []

        # Get Fibonacci levels from different swing periods
        periods = [15, 25, 40]
        for period in periods:
            if len(bars) < period + 5:
                continue

            swing_high, swing_low = self._find_significant_swing(bars, period)
            if swing_high <= swing_low:
                continue

            levels = self.fibonacci_levels(swing_high, swing_low)
            cluster_levels.extend(levels.values())

        # Count how many levels are near current price
        nearby_levels = 0
        margin = current_price * 0.01  # 1% margin

        for level in cluster_levels:
            if abs(current_price - level) <= margin:
                nearby_levels += 1

        if nearby_levels >= 4:
            return 12  # Strong cluster
        elif nearby_levels >= 3:
            return 8  # Moderate cluster
        elif nearby_levels >= 2:
            return 4  # Weak cluster
        else:
            return 0
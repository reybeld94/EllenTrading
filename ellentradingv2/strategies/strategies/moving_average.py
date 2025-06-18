from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from asgiref.sync import async_to_sync


class MovingAverageCrossStrategy(EntryStrategy):
    name = "Moving Average Cross Strategy"

    def __init__(self, strategy_instance=None, short_period=10, long_period=30):
        self.name = "Moving Average Cross Strategy"
        self.short_period = short_period
        self.long_period = long_period
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)

        if len(bars) < self.long_period + 5:  # Extra bars for trend analysis
            return None

        # ✨ ANÁLISIS DE MÚLTIPLES MOVING AVERAGES
        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None
        current_price = current_bar.close

        # Get MA values - both calculated and from indicators
        ma_values = self._get_ma_values(bars, current_bar, prev_bar)
        if not ma_values:
            return None

        # ✅ SOLO AJUSTAR BASE: Primary base = 40 (era 70)
        confidence = 40
        signal_type = None

        # ✨ DETECCIÓN DE SEÑALES MEJORADA: Multiple MA analysis

        # Signal Type 1: Classic Cross (short vs long)
        classic_signal, classic_bonus = self._detect_classic_cross(ma_values, current_price)

        # Signal Type 2: Golden Cross / Death Cross (50 vs 200)
        golden_signal, golden_bonus = self._detect_golden_death_cross(ma_values)

        # Signal Type 3: Multi-MA Alignment
        alignment_signal, alignment_bonus = self._detect_ma_alignment(ma_values, current_price)

        # Signal Type 4: MA Support/Resistance bounce
        bounce_signal, bounce_bonus = self._detect_ma_bounce(bars, ma_values, current_price)

        # Priorizar señales por fuerza
        if golden_signal:  # Golden/Death cross es la más fuerte
            signal_type = golden_signal
            confidence += golden_bonus
        elif classic_signal:
            signal_type = classic_signal
            confidence += classic_bonus
        elif alignment_signal:
            signal_type = alignment_signal
            confidence += alignment_bonus
        elif bounce_signal:
            signal_type = bounce_signal
            confidence += bounce_bonus
        else:
            return None

        # ✨ SISTEMA DE BONUS MEJORADO

        # Bonus 1: MA slope strength (trend momentum)
        slope_bonus = self._calculate_slope_bonus(ma_values, signal_type)
        confidence += slope_bonus

        # Bonus 2: MA separation (decisiveness of signal)
        separation_bonus = self._calculate_separation_bonus(ma_values, signal_type)
        confidence += separation_bonus

        # Bonus 3: Volume confirmation
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 4: Price momentum alignment
        momentum_bonus = self._calculate_momentum_bonus(bars, signal_type, current_price)
        confidence += momentum_bonus

        # Bonus 5: Multiple timeframe context (simulated)
        context_bonus = self._calculate_context_bonus(bars, ma_values, signal_type)
        confidence += context_bonus

        # Bonus 6: Candle confirmation
        candle_bonus = self._calculate_candle_bonus(current_bar, signal_type)
        confidence += candle_bonus

        # Bonus 7: Volatility context (trending vs ranging)
        volatility_bonus = self._calculate_volatility_bonus(bars, ma_values)
        confidence += volatility_bonus

        # Bonus 8: MA convergence/divergence pattern
        convergence_bonus = self._calculate_convergence_bonus(ma_values, bars)
        confidence += convergence_bonus

        confidence = min(int(confidence), 100)

        # ✅ SOLO AJUSTAR THRESHOLD: Primary threshold = 50 (era 70)
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 50)
        if confidence < min_confidence:
            return None

        # Evitar duplicados
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="ma_cross",
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
            source="ma_cross",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        from monitoring.utils import log_event
        async_to_sync(log_event)(
            f"✅ MA CROSS Signal: {signal_type} for {symbol_obj.symbol} | Price: {current_price:.4f} | MA10: {ma_values.get('sma_10', 'N/A')} | MA30: {ma_values.get('sma_30', 'N/A')} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s

    def _get_ma_values(self, bars, current_bar, prev_bar):
        """Obtiene valores de múltiples MAs"""
        try:
            # Calculated MAs (fallback)
            closes = [bar.close for bar in bars]
            calc_short = sum(closes[-self.short_period:]) / self.short_period
            calc_long = sum(closes[-self.long_period:]) / self.long_period
            calc_prev_short = sum(closes[-self.short_period - 1:-1]) / self.short_period if len(
                closes) > self.short_period else calc_short
            calc_prev_long = sum(closes[-self.long_period - 1:-1]) / self.long_period if len(
                closes) > self.long_period else calc_long

            # Indicator MAs (preferred)
            ma_values = {
                'sma_10': self.get_indicator_value(current_bar, "sma_10") or calc_short,
                'sma_20': self.get_indicator_value(current_bar, "sma_20"),
                'sma_30': self.get_indicator_value(current_bar, "sma_30") or calc_long,
                'sma_50': self.get_indicator_value(current_bar, "sma_50"),
                'sma_200': self.get_indicator_value(current_bar, "sma_200"),
                'ema_10': self.get_indicator_value(current_bar, "ema_10"),
                'ema_20': self.get_indicator_value(current_bar, "ema_20"),
                'ema_50': self.get_indicator_value(current_bar, "ema_50"),
                'prev_sma_10': self.get_indicator_value(prev_bar,
                                                        "sma_10") or calc_prev_short if prev_bar else calc_short,
                'prev_sma_30': self.get_indicator_value(prev_bar,
                                                        "sma_30") or calc_prev_long if prev_bar else calc_long,
                'prev_sma_50': self.get_indicator_value(prev_bar, "sma_50") if prev_bar else None,
                'prev_sma_200': self.get_indicator_value(prev_bar, "sma_200") if prev_bar else None,
            }

            return ma_values
        except:
            return None

    def _detect_classic_cross(self, ma_values, current_price):
        """Detecta crossover clásico entre MA corta y larga"""
        short_ma = ma_values.get('sma_10')
        long_ma = ma_values.get('sma_30')
        prev_short = ma_values.get('prev_sma_10')
        prev_long = ma_values.get('prev_sma_30')

        if not all([short_ma, long_ma, prev_short, prev_long]):
            return None, 0

        # Bullish cross: short MA crosses above long MA
        if prev_short <= prev_long and short_ma > long_ma:
            bonus = 15
            # Extra bonus if price is above both MAs
            if current_price > max(short_ma, long_ma):
                bonus += 8
            return SignalType.BUY, bonus

        # Bearish cross: short MA crosses below long MA
        if prev_short >= prev_long and short_ma < long_ma:
            bonus = 15
            # Extra bonus if price is below both MAs
            if current_price < min(short_ma, long_ma):
                bonus += 8
            return SignalType.SELL, bonus

        return None, 0

    def _detect_golden_death_cross(self, ma_values):
        """Detecta Golden Cross (50 sobre 200) y Death Cross"""
        sma_50 = ma_values.get('sma_50')
        sma_200 = ma_values.get('sma_200')
        prev_50 = ma_values.get('prev_sma_50')
        prev_200 = ma_values.get('prev_sma_200')

        if not all([sma_50, sma_200, prev_50, prev_200]):
            return None, 0

        # Golden Cross: MA50 crosses above MA200
        if prev_50 <= prev_200 and sma_50 > sma_200:
            return SignalType.BUY, 25  # Very strong signal

        # Death Cross: MA50 crosses below MA200
        if prev_50 >= prev_200 and sma_50 < sma_200:
            return SignalType.SELL, 25  # Very strong signal

        return None, 0

    def _detect_ma_alignment(self, ma_values, current_price):
        """Detecta alineación de múltiples MAs"""
        mas = [ma_values.get(f'sma_{period}') for period in [10, 20, 50]]
        mas = [ma for ma in mas if ma is not None]

        if len(mas) < 3:
            return None, 0

        # Perfect bullish alignment: shorter MAs above longer MAs
        if mas[0] > mas[1] > mas[2] and current_price > mas[0]:
            return SignalType.BUY, 20

        # Perfect bearish alignment: shorter MAs below longer MAs
        if mas[0] < mas[1] < mas[2] and current_price < mas[0]:
            return SignalType.SELL, 20

        return None, 0

    def _detect_ma_bounce(self, bars, ma_values, current_price):
        """Detecta rebotes en MAs importantes"""
        if len(bars) < 3:
            return None, 0

        sma_20 = ma_values.get('sma_20')
        sma_50 = ma_values.get('sma_50')

        prev_prices = [bars[-3].close, bars[-2].close, current_price]

        for ma_val, ma_name in [(sma_20, 'SMA20'), (sma_50, 'SMA50')]:
            if not ma_val:
                continue

            # Bounce off MA support (bullish)
            if (prev_prices[0] > ma_val and  # Started above
                    prev_prices[1] <= ma_val and  # Touched/went below
                    prev_prices[2] > ma_val):  # Bounced back above
                return SignalType.BUY, 12

            # Rejection at MA resistance (bearish)
            if (prev_prices[0] < ma_val and  # Started below
                    prev_prices[1] >= ma_val and  # Touched/went above
                    prev_prices[2] < ma_val):  # Rejected back below
                return SignalType.SELL, 12

        return None, 0

    def _calculate_slope_bonus(self, ma_values, signal_type):
        """Calcula bonus basado en la pendiente de las MAs"""
        sma_20 = ma_values.get('sma_20')
        prev_sma_20 = ma_values.get('prev_sma_20')

        if not all([sma_20, prev_sma_20]):
            return 0

        slope = (sma_20 - prev_sma_20) / prev_sma_20
        slope_strength = abs(slope)

        bonus = 0
        if slope_strength > 0.01:  # 1%+ slope
            bonus = 12
        elif slope_strength > 0.005:  # 0.5%+ slope
            bonus = 8
        elif slope_strength > 0.001:  # 0.1%+ slope
            bonus = 4

        # Verify slope aligns with signal
        if signal_type == SignalType.BUY and slope > 0:
            return bonus
        elif signal_type == SignalType.SELL and slope < 0:
            return bonus
        else:
            return bonus // 2  # Partial credit for conflicting slope

    def _calculate_separation_bonus(self, ma_values, signal_type):
        """Calcula bonus basado en separación entre MAs"""
        short_ma = ma_values.get('sma_10')
        long_ma = ma_values.get('sma_30')

        if not all([short_ma, long_ma]):
            return 0

        separation = abs(short_ma - long_ma) / long_ma

        if separation > 0.05:  # 5%+ separation
            return 12
        elif separation > 0.02:  # 2%+ separation
            return 8
        elif separation > 0.01:  # 1%+ separation
            return 4
        else:
            return 0  # Too close together

    def _calculate_volume_bonus(self, bars, current_bar):
        """Calcula bonus basado en volumen"""
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
                return 15
            elif volume_ratio > 1.4:
                return 10
            elif volume_ratio > 1.1:
                return 5
            else:
                return 0
        except:
            return 0

    def _calculate_momentum_bonus(self, bars, signal_type, current_price):
        """Calcula bonus basado en momentum del precio"""
        if len(bars) < 5:
            return 0

        price_momentum = (current_price - bars[-5].close) / bars[-5].close
        momentum_strength = abs(price_momentum)

        bonus = 0
        if momentum_strength > 0.03:  # 3%+ momentum
            bonus = 12
        elif momentum_strength > 0.015:  # 1.5%+ momentum
            bonus = 8
        elif momentum_strength > 0.01:  # 1%+ momentum
            bonus = 4

        # Verify momentum aligns with signal
        if signal_type == SignalType.BUY and price_momentum > 0:
            return bonus
        elif signal_type == SignalType.SELL and price_momentum < 0:
            return bonus
        else:
            return 0

    def _calculate_context_bonus(self, bars, ma_values, signal_type):
        """Calcula bonus basado en contexto de mercado"""
        sma_50 = ma_values.get('sma_50')
        sma_200 = ma_values.get('sma_200')

        if not all([sma_50, sma_200]):
            return 0

        # Bull market context (50 > 200)
        if sma_50 > sma_200 and signal_type == SignalType.BUY:
            return 8
        # Bear market context (50 < 200)
        elif sma_50 < sma_200 and signal_type == SignalType.SELL:
            return 8
        else:
            return 0

    def _calculate_candle_bonus(self, current_bar, signal_type):
        """Calcula bonus basado en patrón de vela"""
        candle_body = abs(current_bar.close - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        if signal_type == SignalType.BUY and current_bar.close > current_bar.open and body_ratio > 0.6:
            return 8  # Strong green candle
        elif signal_type == SignalType.SELL and current_bar.close < current_bar.open and body_ratio > 0.6:
            return 8  # Strong red candle
        else:
            return 0

    def _calculate_volatility_bonus(self, bars, ma_values):
        """Calcula bonus basado en volatilidad (trending vs ranging)"""
        if len(bars) < 20:
            return 0

        # Calculate volatility as % range over last 20 bars
        highs = [bar.high for bar in bars[-20:]]
        lows = [bar.low for bar in bars[-20:]]
        volatility = (max(highs) - min(lows)) / sum(bar.close for bar in bars[-20:]) * 20

        # Higher volatility = better for MA cross signals
        if volatility > 0.15:  # High volatility
            return 8
        elif volatility > 0.08:  # Medium volatility
            return 5
        else:
            return 0  # Low volatility (ranging market)

    def _calculate_convergence_bonus(self, ma_values, bars):
        """Calcula bonus por patrones de convergencia/divergencia"""
        if len(bars) < 10:
            return 0

        sma_10 = ma_values.get('sma_10')
        sma_30 = ma_values.get('sma_30')

        if not all([sma_10, sma_30]):
            return 0

        # Check if MAs were converging before the cross
        try:
            old_10 = self.get_indicator_value(bars[-10], "sma_10")
            old_30 = self.get_indicator_value(bars[-10], "sma_30")

            if old_10 and old_30:
                old_separation = abs(old_10 - old_30)
                current_separation = abs(sma_10 - sma_30)

                # MAs were converging (getting closer) before crossing
                if old_separation > current_separation * 1.5:
                    return 8
        except:
            pass

        return 0
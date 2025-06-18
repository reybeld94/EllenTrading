from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from asgiref.sync import async_to_sync


class TripleEMACrossoverStrategy(EntryStrategy):
    name = "Triple EMA Crossover Strategy"

    def __init__(self, strategy_instance=None):
        self.name = "Triple EMA Crossover Strategy"
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.required_bars:
            return None

        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None

        # Get EMA values
        ema_9_curr = self.get_indicator_value(current_bar, "ema_9")
        ema_21_curr = self.get_indicator_value(current_bar, "ema_21")
        ema_55_curr = self.get_indicator_value(current_bar, "ema_55")
        ema_9_prev = self.get_indicator_value(prev_bar, "ema_9") if prev_bar else None
        ema_21_prev = self.get_indicator_value(prev_bar, "ema_21") if prev_bar else None
        ema_55_prev = self.get_indicator_value(prev_bar, "ema_55") if prev_bar else None

        if None in (ema_9_curr, ema_21_curr, ema_55_curr):
            return None

        current_price = current_bar.close
        confidence = 40  # Primary base
        signal_type = None

        # ✨ MEJORA 1: MÚLTIPLES TIPOS DE SEÑALES EMA

        # Signal Type 1: Perfect Triple Crossover (original)
        perfect_signal, perfect_bonus = self._detect_perfect_crossover(
            ema_9_curr, ema_21_curr, ema_55_curr,
            ema_9_prev, ema_21_prev, current_price
        )

        # Signal Type 2: EMA Sequence Alignment
        alignment_signal, alignment_bonus = self._detect_ema_alignment(
            ema_9_curr, ema_21_curr, ema_55_curr, current_price, bars
        )

        # Signal Type 3: EMA Bounce (price bouncing off EMA support/resistance)
        bounce_signal, bounce_bonus = self._detect_ema_bounce(
            bars, ema_9_curr, ema_21_curr, ema_55_curr, current_price
        )

        # Signal Type 4: EMA Convergence/Divergence
        convergence_signal, convergence_bonus = self._detect_ema_convergence(
            bars, ema_9_curr, ema_21_curr, ema_55_curr
        )

        # Priorizar señales por fuerza
        if perfect_signal:
            signal_type = perfect_signal
            confidence += perfect_bonus
        elif alignment_signal:
            signal_type = alignment_signal
            confidence += alignment_bonus
        elif bounce_signal:
            signal_type = bounce_signal
            confidence += bounce_bonus
        elif convergence_signal:
            signal_type = convergence_signal
            confidence += convergence_bonus
        else:
            return None

        # ✨ MEJORA 2: SISTEMA DE BONUS EXPANDIDO

        # Bonus 1: EMA Separation Strength
        separation_bonus = self._calculate_ema_separation_bonus(
            ema_9_curr, ema_21_curr, ema_55_curr, signal_type
        )
        confidence += separation_bonus

        # Bonus 2: EMA Slope Momentum
        slope_bonus = self._calculate_ema_slope_bonus(
            ema_9_curr, ema_21_curr, ema_55_curr,
            ema_9_prev, ema_21_prev, ema_55_prev, signal_type
        )
        confidence += slope_bonus

        # Bonus 3: Volume Confirmation
        volume_bonus = self._calculate_volume_bonus(bars, current_bar)
        confidence += volume_bonus

        # Bonus 4: Price Momentum Alignment
        momentum_bonus = self._calculate_momentum_bonus(bars, signal_type, current_price)
        confidence += momentum_bonus

        # Bonus 5: Swing Breakout (improved original logic)
        swing_bonus = self._calculate_swing_breakout_bonus(bars, current_price, signal_type)
        confidence += swing_bonus

        # Bonus 6: EMA Order Strength
        order_bonus = self._calculate_ema_order_bonus(
            ema_9_curr, ema_21_curr, ema_55_curr, signal_type
        )
        confidence += order_bonus

        # Bonus 7: Trend Consistency
        trend_bonus = self._calculate_trend_consistency_bonus(bars, signal_type)
        confidence += trend_bonus

        # Bonus 8: Candle Confirmation
        candle_bonus = self._calculate_candle_bonus(current_bar, signal_type)
        confidence += candle_bonus

        confidence = min(int(confidence), 100)

        # Threshold check
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 50)
        if confidence < min_confidence:
            return None

        # Avoid duplicates
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="triple_ema_crossover",
            strategy=self.strategy_instance,
            received_at__gte=recent_cutoff
        ).exists()
        if recent_signal:
            return None

        # Create signal
        s = Signal(
            symbol=symbol_obj,
            signal=signal_type,
            price=current_price,
            confidence_score=confidence,
            source="triple_ema_crossover",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        from monitoring.utils import log_event
        async_to_sync(log_event)(
            f"✅ TRIPLE EMA: {signal_type} for {symbol_obj.symbol} | Price: {current_price:.4f} | EMA9: {ema_9_curr:.4f} | EMA21: {ema_21_curr:.4f} | EMA55: {ema_55_curr:.4f} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s

    def _detect_perfect_crossover(self, ema_9, ema_21, ema_55, ema_9_prev, ema_21_prev, price):
        """Detecta crossover perfecto original (mejorado)"""
        if not all([ema_9_prev, ema_21_prev]):
            return None, 0

        # Bullish perfect crossover
        if (ema_9_prev < ema_21_prev and ema_9 > ema_21 and
                ema_9 > ema_55 and ema_21 > ema_55):

            bonus = 25  # Very strong signal

            # Extra bonus if price is above all EMAs
            if price > max(ema_9, ema_21, ema_55):
                bonus += 10

            return SignalType.BUY, bonus

        # Bearish perfect crossover
        if (ema_9_prev > ema_21_prev and ema_9 < ema_21 and
                ema_9 < ema_55 and ema_21 < ema_55):

            bonus = 25  # Very strong signal

            # Extra bonus if price is below all EMAs
            if price < min(ema_9, ema_21, ema_55):
                bonus += 10

            return SignalType.SELL, bonus

        return None, 0

    def _detect_ema_alignment(self, ema_9, ema_21, ema_55, price, bars):
        """Detecta alineación perfecta sin necesidad de crossover"""
        # Perfect bullish alignment: EMA9 > EMA21 > EMA55 and price > EMA9
        if ema_9 > ema_21 > ema_55 and price > ema_9:
            # Check if this is a new alignment (wasn't aligned 3 bars ago)
            if len(bars) >= 4:
                old_bar = bars[-4]
                old_9 = self.get_indicator_value(old_bar, "ema_9")
                old_21 = self.get_indicator_value(old_bar, "ema_21")
                old_55 = self.get_indicator_value(old_bar, "ema_55")

                if old_9 and old_21 and old_55:
                    # Wasn't perfectly aligned before
                    if not (old_9 > old_21 > old_55):
                        return SignalType.BUY, 18

        # Perfect bearish alignment: EMA9 < EMA21 < EMA55 and price < EMA9
        if ema_9 < ema_21 < ema_55 and price < ema_9:
            # Check if this is a new alignment
            if len(bars) >= 4:
                old_bar = bars[-4]
                old_9 = self.get_indicator_value(old_bar, "ema_9")
                old_21 = self.get_indicator_value(old_bar, "ema_21")
                old_55 = self.get_indicator_value(old_bar, "ema_55")

                if old_9 and old_21 and old_55:
                    # Wasn't perfectly aligned before
                    if not (old_9 < old_21 < old_55):
                        return SignalType.SELL, 18

        return None, 0

    def _detect_ema_bounce(self, bars, ema_9, ema_21, ema_55, price):
        """Detecta rebotes en EMAs importantes"""
        if len(bars) < 3:
            return None, 0

        prev_prices = [bars[-3].close, bars[-2].close, price]

        # Test bounce off each EMA
        for ema_val, ema_name in [(ema_9, 'EMA9'), (ema_21, 'EMA21'), (ema_55, 'EMA55')]:
            if not ema_val:
                continue

            # Bullish bounce: price touched EMA from above and bounced up
            if (prev_prices[0] > ema_val and  # Started above
                    prev_prices[1] <= ema_val * 1.002 and  # Touched EMA (0.2% tolerance)
                    prev_prices[2] > ema_val):  # Bounced back above

                bonus = 15 if ema_name == 'EMA21' else 12  # EMA21 is strongest support
                return SignalType.BUY, bonus

            # Bearish bounce: price touched EMA from below and got rejected
            if (prev_prices[0] < ema_val and  # Started below
                    prev_prices[1] >= ema_val * 0.998 and  # Touched EMA (0.2% tolerance)
                    prev_prices[2] < ema_val):  # Rejected back below

                bonus = 15 if ema_name == 'EMA21' else 12  # EMA21 is strongest resistance
                return SignalType.SELL, bonus

        return None, 0

    def _detect_ema_convergence(self, bars, ema_9, ema_21, ema_55):
        """Detecta convergencia/divergencia de EMAs"""
        if len(bars) < 10:
            return None, 0

        # Get older EMA values for comparison
        old_bar = bars[-10]
        old_9 = self.get_indicator_value(old_bar, "ema_9")
        old_21 = self.get_indicator_value(old_bar, "ema_21")
        old_55 = self.get_indicator_value(old_bar, "ema_55")

        if not all([old_9, old_21, old_55]):
            return None, 0

        # Calculate previous separations
        old_sep_9_21 = abs(old_9 - old_21)
        old_sep_21_55 = abs(old_21 - old_55)

        # Calculate current separations
        curr_sep_9_21 = abs(ema_9 - ema_21)
        curr_sep_21_55 = abs(ema_21 - ema_55)

        # Diverging EMAs (expanding) after convergence
        if (old_sep_9_21 < curr_sep_9_21 * 0.7 and  # EMAs were closer before
                old_sep_21_55 < curr_sep_21_55 * 0.7):

            if ema_9 > ema_21 > ema_55:  # Bullish divergence
                return SignalType.BUY, 14
            elif ema_9 < ema_21 < ema_55:  # Bearish divergence
                return SignalType.SELL, 14

        return None, 0

    def _calculate_ema_separation_bonus(self, ema_9, ema_21, ema_55, signal_type):
        """Calcula bonus basado en separación entre EMAs"""
        # Calculate separations
        sep_9_21 = abs(ema_9 - ema_21) / ema_21
        sep_21_55 = abs(ema_21 - ema_55) / ema_55

        total_separation = sep_9_21 + sep_21_55

        if total_separation > 0.04:  # 4%+ total separation
            return 12
        elif total_separation > 0.02:  # 2%+ total separation
            return 8
        elif total_separation > 0.01:  # 1%+ total separation
            return 4
        else:
            return 0

    def _calculate_ema_slope_bonus(self, ema_9, ema_21, ema_55, ema_9_prev, ema_21_prev, ema_55_prev, signal_type):
        """Calcula bonus basado en pendiente de EMAs"""
        if not all([ema_9_prev, ema_21_prev, ema_55_prev]):
            return 0

        # Calculate slopes
        slope_9 = (ema_9 - ema_9_prev) / ema_9_prev
        slope_21 = (ema_21 - ema_21_prev) / ema_21_prev
        slope_55 = (ema_55 - ema_55_prev) / ema_55_prev

        bonus = 0

        if signal_type == SignalType.BUY:
            # All slopes should be positive and increasing
            if slope_9 > 0 and slope_21 > 0 and slope_55 > 0:
                bonus += 8
                # Extra bonus if slopes are accelerating (9 > 21 > 55)
                if slope_9 > slope_21 > slope_55:
                    bonus += 6
        elif signal_type == SignalType.SELL:
            # All slopes should be negative and decreasing
            if slope_9 < 0 and slope_21 < 0 and slope_55 < 0:
                bonus += 8
                # Extra bonus if slopes are accelerating (9 < 21 < 55)
                if slope_9 < slope_21 < slope_55:
                    bonus += 6

        return bonus

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

            if volume_ratio > 1.5:
                return 10
            elif volume_ratio > 1.2:
                return 6
            elif volume_ratio > 1.1:
                return 3
            else:
                return 0
        except:
            return 0

    def _calculate_momentum_bonus(self, bars, signal_type, current_price):
        """Calcula bonus basado en momentum del precio"""
        if len(bars) < 5:
            return 0

        price_momentum = (current_price - bars[-5].close) / bars[-5].close

        if signal_type == SignalType.BUY and price_momentum > 0.02:  # 2%+ upward momentum
            return 8
        elif signal_type == SignalType.SELL and price_momentum < -0.02:  # 2%+ downward momentum
            return 8
        else:
            return 0

    def _calculate_swing_breakout_bonus(self, bars, current_price, signal_type):
        """Versión mejorada del swing breakout original"""
        if len(bars) < 10:
            return 0

        # Use different lookback periods for better detection
        highs = [bar.high for bar in bars[-10:]]
        lows = [bar.low for bar in bars[-10:]]

        # Exclude current bar for swing calculation
        swing_high = max(highs[:-1])
        swing_low = min(lows[:-1])

        if signal_type == SignalType.BUY and current_price > swing_high:
            # Extra bonus for strength of breakout
            breakout_strength = (current_price - swing_high) / swing_high
            base_bonus = 10
            if breakout_strength > 0.02:  # 2%+ breakout
                base_bonus += 8
            elif breakout_strength > 0.01:  # 1%+ breakout
                base_bonus += 4
            return base_bonus

        elif signal_type == SignalType.SELL and current_price < swing_low:
            # Extra bonus for strength of breakdown
            breakdown_strength = (swing_low - current_price) / swing_low
            base_bonus = 10
            if breakdown_strength > 0.02:  # 2%+ breakdown
                base_bonus += 8
            elif breakdown_strength > 0.01:  # 1%+ breakdown
                base_bonus += 4
            return base_bonus

        else:
            return 0

    def _calculate_ema_order_bonus(self, ema_9, ema_21, ema_55, signal_type):
        """Calcula bonus por orden perfecto de EMAs"""
        if signal_type == SignalType.BUY and ema_9 > ema_21 > ema_55:
            return 8  # Perfect bullish order
        elif signal_type == SignalType.SELL and ema_9 < ema_21 < ema_55:
            return 8  # Perfect bearish order
        else:
            return 0

    def _calculate_trend_consistency_bonus(self, bars, signal_type):
        """Calcula bonus por consistencia de tendencia"""
        if len(bars) < 10:
            return 0

        # Simple trend analysis over last 10 bars
        prices = [bar.close for bar in bars[-10:]]

        if signal_type == SignalType.BUY:
            # Count ascending moves
            ascending = sum(1 for i in range(1, len(prices)) if prices[i] > prices[i - 1])
            if ascending >= 7:  # 7 out of 9 up moves
                return 6
        elif signal_type == SignalType.SELL:
            # Count descending moves
            descending = sum(1 for i in range(1, len(prices)) if prices[i] < prices[i - 1])
            if descending >= 7:  # 7 out of 9 down moves
                return 6

        return 0

    def _calculate_candle_bonus(self, current_bar, signal_type):
        """Calcula bonus basado en patrón de vela"""
        candle_body = abs(current_bar.close - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        if signal_type == SignalType.BUY and current_bar.close > current_bar.open and body_ratio > 0.6:
            return 6  # Strong green candle
        elif signal_type == SignalType.SELL and current_bar.close < current_bar.open and body_ratio > 0.6:
            return 6  # Strong red candle
        else:
            return 0
from signals.signal import Signal
from core.models.enums import SignalType
from core.models.symbol import Symbol
from strategies.base.base_entry import EntryStrategy
from django.utils.timezone import now, timedelta
from asgiref.sync import async_to_sync


class MACDCrossoverStrategy(EntryStrategy):
    name = "MACD Crossover Strategy"

    def __init__(self, strategy_instance=None):
        self.name = "MACD Crossover Strategy"
        super().__init__(strategy_instance)

    def should_generate_signal(self, symbol: Symbol, execution_mode="simulated", candles=None) -> Signal | None:
        bars = candles or self.get_candles(symbol, execution_mode)
        if len(bars) < self.required_bars:
            return None

        current_bar = bars[-1]
        prev_bar = bars[-2] if len(bars) >= 2 else None

        # Obtener valores MACD actuales
        curr_macd = self.get_indicator_value(current_bar, "macd")
        curr_signal = self.get_indicator_value(current_bar, "macd_signal")
        curr_hist = self.get_indicator_value(current_bar, "macd_hist")

        # Obtener valores MACD previos
        prev_macd = self.get_indicator_value(prev_bar, "macd") if prev_bar else None
        prev_signal = self.get_indicator_value(prev_bar, "macd_signal") if prev_bar else None
        prev_hist = self.get_indicator_value(prev_bar, "macd_hist") if prev_bar else None

        if None in (curr_macd, curr_signal, curr_hist):
            return None

        confidence = 65  # ⬆️ Base más alta (era 50)
        signal_type = None

        # ✨ NUEVA LÓGICA: Múltiples tipos de señales MACD

        # Signal Type 1: Classic MACD Line Crossover
        crossover_signal, crossover_bonus = self._detect_macd_crossover(
            curr_macd, curr_signal, prev_macd, prev_signal, curr_hist, prev_hist
        )

        # Signal Type 2: MACD Zero Line Crossover
        zero_cross_signal, zero_cross_bonus = self._detect_zero_crossover(
            curr_macd, prev_macd, curr_hist
        )

        # Signal Type 3: Histogram Divergence/Momentum
        hist_signal, hist_bonus = self._detect_histogram_signals(
            bars, curr_hist, prev_hist
        )

        # Signal Type 4: MACD Divergence with Price
        div_signal, div_bonus = self._detect_macd_divergence(bars)

        # Priorizar señales por fuerza
        if crossover_signal:
            signal_type = crossover_signal
            confidence += crossover_bonus
        elif zero_cross_signal:
            signal_type = zero_cross_signal
            confidence += zero_cross_bonus
        elif hist_signal:
            signal_type = hist_signal
            confidence += hist_bonus
        elif div_signal:
            signal_type = div_signal
            confidence += div_bonus
        else:
            return None

        # ✨ SISTEMA DE BONUS MEJORADO

        # Bonus 1: MACD position relative to zero
        if curr_macd > 0 and signal_type == SignalType.BUY:
            confidence += 8  # Bullish momentum confirmed
        elif curr_macd < 0 and signal_type == SignalType.SELL:
            confidence += 8  # Bearish momentum confirmed
        elif abs(curr_macd) < 0.5:  # Close to zero line
            confidence += 5  # Neutral zone, more reliable signals

        # Bonus 2: Histogram momentum strength
        if prev_hist:
            hist_momentum = curr_hist - prev_hist
            hist_strength = abs(hist_momentum)

            if hist_strength > 0.3:
                confidence += 15  # Strong momentum
            elif hist_strength > 0.15:
                confidence += 10  # Moderate momentum
            elif hist_strength > 0.05:
                confidence += 5  # Mild momentum

            # Check if histogram momentum aligns with signal
            if signal_type == SignalType.BUY and hist_momentum > 0:
                confidence += 8  # Histogram confirming bullish
            elif signal_type == SignalType.SELL and hist_momentum < 0:
                confidence += 8  # Histogram confirming bearish

        # Bonus 3: Speed of crossover (faster = more decisive)
        if prev_macd and prev_signal:
            prev_separation = abs(prev_macd - prev_signal)
            curr_separation = abs(curr_macd - curr_signal)
            crossover_speed = curr_separation - prev_separation

            if crossover_speed > 0.1:
                confidence += 12  # Fast decisive crossover
            elif crossover_speed > 0.05:
                confidence += 8  # Moderate speed crossover

        # Bonus 4: Volume confirmation
        try:
            current_volume = getattr(current_bar, 'volume', None) or self.get_indicator_value(current_bar, "volume")
            if current_volume and len(bars) >= 10:
                volumes = []
                for bar in bars[-10:]:
                    vol = getattr(bar, 'volume', None) or self.get_indicator_value(bar, "volume")
                    if vol:
                        volumes.append(vol)

                if volumes:
                    avg_volume = sum(volumes) / len(volumes)
                    volume_ratio = current_volume / avg_volume

                    if volume_ratio > 1.5:
                        confidence += 12  # High volume confirmation
                    elif volume_ratio > 1.2:
                        confidence += 8  # Moderate volume
        except:
            pass

        # Bonus 5: Price momentum confirmation
        current_price = current_bar.close
        if len(bars) >= 3:
            price_momentum = (current_price - bars[-3].close) / bars[-3].close

            if signal_type == SignalType.BUY and price_momentum > 0.01:
                confidence += 10  # Price momentum confirms bullish signal
            elif signal_type == SignalType.SELL and price_momentum < -0.01:
                confidence += 10  # Price momentum confirms bearish signal

        # Bonus 6: Trend alignment (SMA confirmation)
        try:
            sma_20 = self.get_indicator_value(current_bar, "sma_20")
            if sma_20:
                if signal_type == SignalType.BUY and current_price > sma_20:
                    confidence += 10  # Uptrend confirmed
                elif signal_type == SignalType.SELL and current_price < sma_20:
                    confidence += 10  # Downtrend confirmed
        except:
            pass

        # Bonus 7: Multiple timeframe confirmation (if available)
        # This would require checking longer timeframe MACD, but we can simulate
        if len(bars) >= 10:
            # Look at MACD trend over longer period
            older_macd = self.get_indicator_value(bars[-10], "macd") if len(bars) >= 10 else None
            if older_macd:
                macd_trend = curr_macd - older_macd
                if signal_type == SignalType.BUY and macd_trend > 0:
                    confidence += 8  # MACD trending up
                elif signal_type == SignalType.SELL and macd_trend < 0:
                    confidence += 8  # MACD trending down

        # Bonus 8: Candle confirmation
        candle_body = abs(current_price - current_bar.open)
        candle_range = current_bar.high - current_bar.low
        body_ratio = candle_body / candle_range if candle_range > 0 else 0

        if signal_type == SignalType.BUY and current_price > current_bar.open and body_ratio > 0.6:
            confidence += 8  # Strong green candle
        elif signal_type == SignalType.SELL and current_price < current_bar.open and body_ratio > 0.6:
            confidence += 8  # Strong red candle

        confidence = min(int(confidence), 100)

        # Verificar threshold
        min_confidence = getattr(self.strategy_instance, "confidence_threshold", 70)
        if confidence < min_confidence:
            return None

        # Evitar duplicados
        symbol_obj = Symbol.objects.get(symbol=symbol) if isinstance(symbol, str) else symbol
        timeframe_minutes = int(self.timeframe.replace("m", "")) if "m" in self.timeframe else 60
        recent_cutoff = now() - timedelta(minutes=timeframe_minutes)
        recent_signal = Signal.objects.filter(
            symbol=symbol_obj,
            signal=signal_type,
            source="macd_cross",
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
            source="macd_cross",
            strategy=self.strategy_instance,
            timeframe=self.timeframe
        )
        s.timestamp = getattr(current_bar, "timestamp", getattr(current_bar, "start_time", None))
        s.received_at = s.timestamp

        from monitoring.utils import log_event
        async_to_sync(log_event)(
            f"✅ MACD Signal: {signal_type} for {symbol_obj.symbol} | MACD: {curr_macd:.4f} vs Signal: {curr_signal:.4f} | Hist: {curr_hist:.4f} | Confidence: {confidence}",
            source='strategies', level='INFO')
        return s

    def _detect_macd_crossover(self, curr_macd, curr_signal, prev_macd, prev_signal, curr_hist, prev_hist):
        """Detecta crossovers clásicos de línea MACD"""
        if not all([prev_macd, prev_signal]):
            return None, 0

        # Bullish crossover: MACD crosses above signal line
        if prev_macd <= prev_signal and curr_macd > curr_signal:
            # Strength based on how close to zero and histogram confirmation
            bonus = 15
            if abs(curr_macd) < 0.2:  # Near zero line
                bonus += 8
            if curr_hist > prev_hist:  # Histogram expanding
                bonus += 5
            return SignalType.BUY, bonus

        # Bearish crossover: MACD crosses below signal line
        if prev_macd >= prev_signal and curr_macd < curr_signal:
            bonus = 15
            if abs(curr_macd) < 0.2:  # Near zero line
                bonus += 8
            if curr_hist < prev_hist:  # Histogram expanding
                bonus += 5
            return SignalType.SELL, bonus

        return None, 0

    def _detect_zero_crossover(self, curr_macd, prev_macd, curr_hist):
        """Detecta crossovers de línea zero"""
        if not prev_macd:
            return None, 0

        # MACD crosses above zero (bullish)
        if prev_macd <= 0 and curr_macd > 0:
            bonus = 12
            if curr_hist > 0:  # Histogram also positive
                bonus += 8
            return SignalType.BUY, bonus

        # MACD crosses below zero (bearish)
        if prev_macd >= 0 and curr_macd < 0:
            bonus = 12
            if curr_hist < 0:  # Histogram also negative
                bonus += 8
            return SignalType.SELL, bonus

        return None, 0

    def _detect_histogram_signals(self, bars, curr_hist, prev_hist):
        """Detecta señales basadas en momentum del histograma"""
        if not prev_hist or len(bars) < 5:
            return None, 0

        # Get histogram trend over last 3 bars
        hist_values = []
        for bar in bars[-4:]:  # Last 4 bars including current
            hist = self.get_indicator_value(bar, "macd_hist")
            if hist is not None:
                hist_values.append(hist)

        if len(hist_values) < 3:
            return None, 0

        # Check for histogram momentum reversal
        recent_trend = hist_values[-1] - hist_values[-3]  # 3-bar trend

        # Bullish histogram reversal (was declining, now increasing)
        if recent_trend > 0.1 and hist_values[-1] > hist_values[-2]:
            return SignalType.BUY, 10

        # Bearish histogram reversal (was increasing, now declining)
        if recent_trend < -0.1 and hist_values[-1] < hist_values[-2]:
            return SignalType.SELL, 10

        return None, 0

    def _detect_macd_divergence(self, bars):
        """Detecta divergencias entre MACD y precio (básico)"""
        if len(bars) < 10:
            return None, 0

        # Get recent price highs/lows and corresponding MACD values
        try:
            recent_prices = [bar.close for bar in bars[-10:]]
            recent_macd = [self.get_indicator_value(bar, "macd") for bar in bars[-10:]]

            if any(v is None for v in recent_macd):
                return None, 0

            # Simple divergence: price making new highs but MACD not
            if recent_prices[-1] > max(recent_prices[:-1]) and recent_macd[-1] < max(recent_macd[:-1]):
                return SignalType.SELL, 8  # Bearish divergence

            # Price making new lows but MACD not
            if recent_prices[-1] < min(recent_prices[:-1]) and recent_macd[-1] > min(recent_macd[:-1]):
                return SignalType.BUY, 8  # Bullish divergence

        except:
            pass

        return None, 0
# backtest_watcher.py

from typing import List
from backtesting.models import HistoricalMarketDataPoint

class BacktestWatcher:
    def __init__(self, trade, future_candles: List[HistoricalMarketDataPoint]):
        self.trade = trade
        self.candles = future_candles
        self.entry_price = trade.price
        self.direction = trade.direction.lower()
        self.sl = getattr(trade, "stop_loss", None)
        self.tp = getattr(trade, "take_profit", None)
        self.trailing = getattr(trade, "trailing_stop", None)
        self.trailing_level = getattr(trade, "trailing_level", None)
        self.highest_price = self.entry_price if self.direction == "buy" else None
        self.lowest_price = self.entry_price if self.direction == "sell" else None

    def simulate(self):
        for candle in self.candles:
            high = candle.high
            low = candle.low

            # Trailing Stop
            if self.trailing is not None and self.trailing_level is not None:
                if self.direction == "buy":
                    if high > self.highest_price:
                        self.highest_price = high
                        self.trailing_level = self.highest_price * (1 - self.trailing)
                    if low <= self.trailing_level:

                        return self._close(candle, self.trailing_level, "Trailing Stop Hit")
                else:
                    if low < self.lowest_price:
                        self.lowest_price = low
                        self.trailing_level = self.lowest_price * (1 + self.trailing)
                    if high >= self.trailing_level:

                        return self._close(candle, self.trailing_level, "Trailing Stop Hit")

            # Stop Loss
            if self.sl:
                if self.direction == "buy" and low <= self.sl:

                    return self._close(candle, self.sl, "Stop Loss Hit")
                elif self.direction == "sell" and high >= self.sl:

                    return self._close(candle, self.sl, "Stop Loss Hit")

            # Take Profit
            if self.tp:
                if self.direction == "buy" and high >= self.tp:

                    return self._close(candle, self.tp, "Take Profit Hit")
                elif self.direction == "sell" and low <= self.tp:

                    return self._close(candle, self.tp, "Take Profit Hit")

        # Cierre al final
        return self._close(self.candles[-1], self.candles[-1].close, "Closed at end of backtest")

    def _close(self, candle, price, reason):
        pnl = self._calculate_pnl(price)
        return {
            "exit_price": price,
            "exit_time": candle.timestamp,
            "reason": reason,
            "pnl": round(pnl, 2)
        }

    def _calculate_pnl(self, exit_price):
        if self.direction == "buy":
            return exit_price - self.entry_price
        else:
            return self.entry_price - exit_price

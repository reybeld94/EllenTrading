# simulate_trades.py
import django
import os

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ellentradingv2.settings")
django.setup()

from backtesting.strategies.backtest_strategy_runner import run_entry_strategies
from backtesting.models.HistoricalSignal import Signal
from backtesting.models.HistoricalMarketDataPoint import HistoricalMarketDataPoint
from collections import defaultdict
from datetime import timedelta

# CONFIGURACIÓN
SYMBOL = "AAPL"
TIMEFRAMES = ["5m", "15m", "1h", "1d"]
INITIAL_BALANCE = 1000.0
TRAILING_PCT = 1.0  # Trailing stop %


class PermissiveRiskManager:
    def __init__(self, signal, capital=1000, risk_pct=1.0, tp_ratio=2.0, sl_ratio=1.0):
        self.signal = signal
        self.capital = capital
        self.risk_pct = risk_pct
        self.tp_ratio = tp_ratio
        self.sl_ratio = sl_ratio

    def calculate_position_size(self, price):
        max_allocation = self.capital * self.risk_pct
        qty = int(max_allocation // price)
        print(f"💡 Posición calculada: {qty} unidades @ ${price:.2f} con ${self.capital:.2f}")
        return qty if qty > 0 else None

    def analyze(self, price):
        qty = self.calculate_position_size(price)
        if qty is None:
            return None

        direction = self.signal.signal.lower()
        tp = price * (1 + self.tp_ratio / 100) if direction == "buy" else price * (1 - self.tp_ratio / 100)
        sl = price * (1 - self.sl_ratio / 100) if direction == "buy" else price * (1 + self.sl_ratio / 100)

        return {
            "symbol": self.signal.market_data.symbol,
            "direction": direction,
            "entry_price": price,
            "qty": qty,
            "confidence": self.signal.confidence_score,
            "strategy": self.signal.strategy.name if self.signal.strategy else "Unknown",
            "tp": tp,
            "sl": sl,
            "signal_obj": self.signal
        }


# Ejecutar backtest de señales
print("🚀 Generando señales de entrada para todas las estrategias...")
run_entry_strategies(symbol_code=SYMBOL)

for tf in TIMEFRAMES:
    print(f"\n🔍 Simulando timeframe: {tf}")
    balance = INITIAL_BALANCE
    open_position = None
    closed_trades = []

    signals = Signal.objects.filter(
        timeframe=tf,
        is_from_backtest=True,
        market_data__symbol=SYMBOL
    ).order_by("timestamp").select_related("market_data", "strategy")

    signal_groups = defaultdict(list)
    for s in signals:
        signal_groups[s.timestamp].append(s)

    sorted_timestamps = sorted(signal_groups.keys())

    for timestamp in sorted_timestamps:
        group = signal_groups[timestamp]
        price = group[0].market_data.close

        if not open_position:
            for signal in group:
                rm = PermissiveRiskManager(signal, capital=balance)
                trade = rm.analyze(price)
                if trade:
                    qty = trade["qty"]
                    cost = qty * price
                    open_position = {
                        "entry_price": price,
                        "qty": qty,
                        "entry_time": timestamp,
                        "strategy": trade["strategy"],
                        "tp": trade["tp"],
                        "sl": trade["sl"],
                        "side": trade["direction"],
                        "max_price": price if trade["direction"] == "buy" else None,
                        "min_price": price if trade["direction"] == "sell" else None,
                    }
                    balance -= cost
                    print(f"✅ Trade ejecutado: {qty} @ {price:.2f}, TP={trade['tp']:.2f}, SL={trade['sl']:.2f}")
                    break
        else:
            curr_price = price
            side = open_position["side"]

            # actualizar máximos/mínimos para trailing stop
            if side == "buy":
                open_position["max_price"] = max(open_position["max_price"], curr_price)
                trail_stop = open_position["max_price"] * (1 - TRAILING_PCT / 100)
                sl_hit = curr_price <= trail_stop
                tp_hit = curr_price >= open_position["tp"]
            else:
                open_position["min_price"] = min(open_position["min_price"], curr_price)
                trail_stop = open_position["min_price"] * (1 + TRAILING_PCT / 100)
                sl_hit = curr_price >= trail_stop
                tp_hit = curr_price <= open_position["tp"]

            if sl_hit or tp_hit:
                sell_price = curr_price
                proceeds = open_position["qty"] * sell_price
                pnl = proceeds - open_position["qty"] * open_position["entry_price"]
                balance += proceeds
                closed_trades.append({
                    "entry_time": open_position["entry_time"],
                    "exit_time": timestamp,
                    "entry_price": open_position["entry_price"],
                    "exit_price": sell_price,
                    "strategy": open_position["strategy"],
                    "pnl": pnl
                })
                print(f"💥 Trade cerrado ({'TP' if tp_hit else 'TRAILING STOP'}) @ {sell_price:.2f} | PnL = {pnl:.2f}")
                open_position = None

    # Calcular equity final
    final_equity = balance
    if open_position:
        last_price = HistoricalMarketDataPoint.objects.filter(
            symbol=SYMBOL, timeframe=tf
        ).order_by("-timestamp").first().close
        final_equity += open_position["qty"] * last_price

    # Resumen final
    total_trades = len(closed_trades)
    wins = sum(1 for t in closed_trades if t["pnl"] > 0)
    win_rate = round((wins / total_trades) * 100, 2) if total_trades > 0 else 0.0
    net_profit = sum(t["pnl"] for t in closed_trades)

    print("\n📊 TRADE SUMMARY")
    print(f"⏰ Timeframe: {tf}")
    print(f"💰 Initial Balance: ${INITIAL_BALANCE:.2f}")
    print(f"📈 Final Balance (Cash): ${balance:.2f}")
    print(f"💼 Open Positions Value: ${final_equity - balance:.2f}")
    print(f"🧮 Total Portfolio Equity: ${final_equity:.2f}")
    print(f"📉 Total Trades: {total_trades}")
    print(f"📊 Net Profit (closed only): ${net_profit:.2f}")
    print(f"✅ Win Rate: {win_rate}%")

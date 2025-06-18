# permissive_risk_manager.py

class PermissiveRiskManager:
    def __init__(self, signal, capital=1000, risk_pct=0.05, tp_ratio=2.0, sl_ratio=1.0, trailing_ratio=0.5):
        self.signal = signal
        self.capital = capital
        self.risk_pct = risk_pct
        self.tp_ratio = tp_ratio
        self.sl_ratio = sl_ratio
        self.trailing_ratio = trailing_ratio

    def calculate_position_size(self, price):
        max_allocation = self.capital * self.risk_pct
        qty = int(max_allocation // price)
        return qty if qty > 0 else None

    def analyze(self, price):
        print(f"💡 Calculando posición para ${price:.2f} con capital ${self.capital:.2f}")

        qty = self.calculate_position_size(price)
        if qty is None:
            return None

        direction = self.signal.signal.name.lower()  # "buy" o "sell"
        tp = price * (1 + self.tp_ratio / 100) if direction == "buy" else price * (1 - self.tp_ratio / 100)
        sl = price * (1 - self.sl_ratio / 100) if direction == "buy" else price * (1 + self.sl_ratio / 100)
        trailing = price * (1 + self.trailing_ratio / 100) if direction == "buy" else price * (1 - self.trailing_ratio / 100)

        return {
            "symbol": self.signal.market_data.symbol,
            "direction": direction,
            "entry_price": price,
            "qty": qty,
            "confidence": self.signal.confidence_score,
            "strategy": self.signal.strategy.name if self.signal.strategy else "Unknown",
            "tp": tp,
            "sl": sl,
            "trailing_stop": trailing,
            "signal_obj": self.signal
        }

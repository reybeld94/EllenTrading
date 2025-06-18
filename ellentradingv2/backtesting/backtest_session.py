from typing import List
from datetime import datetime

class BacktestSession:
    def __init__(self, initial_balance: float, trades: List):
        self.initial_balance = initial_balance
        self.trades = trades
        self.closed_trades = [t for t in trades if hasattr(t, 'closed_at')]
        self._calculate_summary()

    def _calculate_summary(self):
        self.total_pnl = sum(t.pnl for t in self.closed_trades)
        self.final_balance = self.initial_balance + self.total_pnl
        self.win_trades = [t for t in self.closed_trades if t.pnl > 0]
        self.loss_trades = [t for t in self.closed_trades if t.pnl <= 0]
        self.winrate = round(len(self.win_trades) / len(self.closed_trades) * 100, 2) if self.closed_trades else 0
        self.total_trades = len(self.closed_trades)

        # Optional: equity curve
        self.equity_curve = []
        equity = self.initial_balance
        for t in sorted(self.closed_trades, key=lambda x: x.closed_at):
            equity += t.pnl
            self.equity_curve.append({
                "date": t.closed_at,
                "equity": round(equity, 2)
            })

    def get_summary(self):
        return {
            "Initial Balance": round(self.initial_balance, 2),
            "Final Balance": round(self.final_balance, 2),
            "Net PnL": round(self.total_pnl, 2),
            "Total Trades": self.total_trades,
            "Win Trades": len(self.win_trades),
            "Loss Trades": len(self.loss_trades),
            "Winrate": f"{self.winrate}%",
            "Equity Curve": self.equity_curve
        }

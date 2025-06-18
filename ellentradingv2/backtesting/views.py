# api/views.py
from backtesting.models import HistoricalMarketDataPoint
from django.db.models import Min, Max
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from datetime import datetime
from core.models.symbol import Symbol
from strategies.models import OpenStrategy
from .backtest_runner import BacktestRunner
from .backtest_session import BacktestSession

class BacktestView(APIView):
    def post(self, request):
        try:
            symbol_name = request.data["symbol"]
            strategy_ids = request.data["strategy_ids"]
            start_date = datetime.fromisoformat(request.data["start_date"])
            end_date = datetime.fromisoformat(request.data["end_date"])
            initial_balance = float(request.data["initial_balance"])

            symbol = Symbol.objects.get(symbol=symbol_name)
            strategies = list(OpenStrategy.objects.filter(id__in=strategy_ids))

            runner = BacktestRunner(symbol, initial_balance, strategies, start_date, end_date)
            signals, trades = runner.run()

            session = BacktestSession(initial_balance, trades)
            summary = session.get_summary()

            trades_data = [
                {
                    "symbol": t.symbol.symbol,
                    "entry_price": t.price,
                    "exit_price": getattr(t, "exit_price", None),
                    "pnl": getattr(t, "pnl", None),
                    "closed_at": getattr(t, "closed_at", None),
                    "timestamp": getattr(t, "timestamp", None),  # 🔥 fecha de entrada
                    "strategy": t.strategy,
                    "direction": t.direction,
                    "notes": getattr(t, "notes", "")
                }
                for t in trades
            ]

            return Response({
                "summary": summary,
                "trades": trades_data
            })

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

class HistoricalSymbolsView(APIView):
    def get(self, request):
        qs = HistoricalMarketDataPoint.objects.values("symbol").annotate(
            start=Min("timestamp"),
            end=Max("timestamp")
        )
        return Response(list(qs))

class StrategyListView(APIView):
    def get(self, request):
        qs = OpenStrategy.objects.filter(is_active=True).values("id", "name")
        return Response(list(qs))
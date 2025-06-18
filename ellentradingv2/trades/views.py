from rest_framework import viewsets
from trades.models.trade import Trade
from trades.serializers import TradeSerializer
from rest_framework.response import Response
from rest_framework.decorators import api_view
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny
from trades.models.portfolio import Portfolio, Position
from trades.serializers import PortfolioSerializer
from streaming.websocket.helpers import emit_trade
from django.utils.timezone import now
from rest_framework import status
from asgiref.sync import async_to_sync
from django.db.models import Avg, Max, Sum, Count
from monitoring.utils import log_event
from asgiref.sync import async_to_sync
from trades.logic.trade_closer import close_trade_manually_unified

class TradeViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = TradeSerializer

    def get_queryset(self):
        status = self.request.query_params.get("status")
        qs = Trade.objects.all().order_by("-executed_at")
        if status:
            return qs.filter(status=status.upper())
        return qs



@api_view(["GET"])
def trade_metrics(request):
    trades = Trade.objects.filter(status="CLOSED")

    total = trades.count()
    wins = trades.filter(pnl__gt=0).count()
    losses = trades.filter(pnl__lt=0).count()
    win_rate = (wins / total * 100) if total > 0 else 0
    total_pnl = sum(t.pnl for t in trades if t.pnl is not None)

    return Response({
        "total_trades": total,
        "wins": wins,
        "losses": losses,
        "win_rate": round(win_rate, 2),
        "total_pnl": round(total_pnl, 2)
    })

class PortfolioView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        portfolio = Portfolio.objects.get(name="Simulado")
        serializer = PortfolioSerializer(portfolio)
        return Response(serializer.data)


@api_view(["POST"])
def close_trade_manually(request, trade_id):
    """
    Cierre manual de trades usando función centralizada
    """
    try:
        result = close_trade_manually_unified(trade_id)

        if result["success"]:
            return Response({
                "message": f"Trade #{trade_id} cerrado exitosamente",
                "pnl": result["pnl"],
                "exit_price": result["exit_price"],
                "new_balance": result["new_balance"]
            }, status=status.HTTP_200_OK)
        else:
            return Response({
                "error": result["error"]
            }, status=status.HTTP_400_BAD_REQUEST)

    except Exception as e:
        async_to_sync(log_event)(f"❌ Error en close_trade_manually: {e}", source='trades', level='ERROR')
        return Response({
            "error": f"Error interno: {str(e)}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

@api_view(["POST"])
def alpaca_webhook(request):
    try:
        data = request.data
        event = data.get("event")
        order = data.get("order", {})
        order_id = order.get("id")
        status = order.get("status")
        side = order.get("side")

        if event != "fill" or status != "filled" or side != "sell":
            return Response({"detail": "Ignored"}, status=200)

        # Buscar el trade por order_id
        trade = Trade.objects.filter(order_id=order_id).first()
        if not trade:
            return Response({"detail": "Trade not found"}, status=404)

        trade.status = "CLOSED"
        trade.close_time = now()
        trade.notes += "\nAuto cerrado desde Alpaca Webhook."
        trade.save()

        return Response({"detail": f"Trade {trade.id} marcado como CLOSED"}, status=200)

    except Exception as e:
        return Response({"error": str(e)}, status=500)


@api_view(["GET"])
def get_trading_metrics(request):
    trades = Trade.objects.filter(status="CLOSED")

    metrics = trades.aggregate(
        total=Count("id"),
        total_pnl=Sum("pnl"),
        avg_pnl=Avg("pnl"),
        avg_drawdown=Avg("max_drawdown"),
        max_drawdown=Max("max_drawdown"),
    )

    return Response({
        "total_trades": metrics["total"] or 0,
        "total_pnl": round(metrics["total_pnl"] or 0, 2),
        "avg_pnl": round(metrics["avg_pnl"] or 0, 2),
        "avg_drawdown": round(metrics["avg_drawdown"] or 0, 2),
        "max_drawdown": round(metrics["max_drawdown"] or 0, 2),
    })


from rest_framework.decorators import api_view
from rest_framework.response import Response
from core.models.marketdatapoint import MarketDataPoint
from core.serializers import MarketDataPointSerializer
from core.models.symbol import Symbol
from core.serializers import SymbolSerializer

@api_view(["GET"])
def get_recent_market_data(request, ticker):
    tf = request.GET.get("tf", "1m")
    points = (
        MarketDataPoint.objects
        .filter(symbol__symbol=ticker, timeframe=tf)
        .order_by("-start_time")[:300]
    )
    return Response(MarketDataPointSerializer(points[::-1], many=True).data)


@api_view(["GET"])
def list_symbols(request):
    symbols = Symbol.objects.filter(is_active=True)
    serializer = SymbolSerializer(symbols, many=True)
    return Response(serializer.data)
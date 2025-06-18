from signals.serializers import SignalSerializer
from rest_framework import viewsets
from signals.signal import Signal

class SignalViewSet(viewsets.ModelViewSet):
    serializer_class = SignalSerializer

    def get_queryset(self):
        queryset = Signal.objects.all().order_by("-received_at")
        limit = self.request.query_params.get("limit")
        if limit:
            return queryset[:int(limit)]
        return queryset



from strategies.models import OpenStrategy
from strategies.serializers import OpenStrategySerializer
from rest_framework import viewsets
from rest_framework.response import Response
from rest_framework import status
from monitoring.utils import log_event
from asgiref.sync import async_to_sync

class OpenStrategyViewSet(viewsets.ModelViewSet):
    queryset = OpenStrategy.objects.all()
    serializer_class = OpenStrategySerializer

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=True)
        if not serializer.is_valid():
            async_to_sync(log_event)(f"❌ ERROR EN SERIALIZER: {serializer.errors}")
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        self.perform_update(serializer)
        return Response(serializer.data)
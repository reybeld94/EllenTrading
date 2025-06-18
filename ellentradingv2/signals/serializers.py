from signals.signal import Signal
from rest_framework import serializers

class SignalSerializer(serializers.ModelSerializer):
    symbol = serializers.StringRelatedField()
    strategy = serializers.StringRelatedField()
    confidence_score = serializers.IntegerField()

    class Meta:
        model = Signal
        fields = "__all__"
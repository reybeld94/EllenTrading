from rest_framework import serializers
from strategies.models import OpenStrategy

class OpenStrategySerializer(serializers.ModelSerializer):
    class Meta:
        model = OpenStrategy
        fields = '__all__'